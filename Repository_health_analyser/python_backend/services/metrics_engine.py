"""
metrics_engine.py — Deterministic code health metric computation.

What this module computes:
  1. Cyclomatic Complexity (per function, per file, per commit)
     Using radon's `cc_visit()` — standard McCabe complexity measure.
     Complexity 1 = one path, 10+ = risky, 20+ = untestable.

  2. Coupling (fan-in, fan-out from the dependency graph)
     Fan-out = how many modules/functions this code depends on.
     Fan-in  = how many modules/functions depend on this code.
     High coupling = fragile code (changes break other things).

  3. Churn Risk = change_frequency × coupling_score (per file)
     Files that change often AND are highly coupled are the riskiest.
     This is the "hotspot" metric — multiply it by coupling to find
     architectural danger zones.

  4. Spike detection: if complexity jumps > SPIKE_THRESHOLD% between two
     consecutive commits, flag that commit as a "spike commit". This is the
     gate for LLM Call 1 (spike explainer).

Libraries:
  - radon : Pure-Python cyclomatic complexity calculator.
            `cc_visit(source)` returns a list of Function objects with
            `complexity` (int), `name`, `lineno` attributes.

Design notes:
  All metric values are stored as floats in the `commits` table.
  Churn and coupling are normalized to [0, 1] range when computing the
  composite risk_score for the hotspot heatmap.
"""

import json
import logging
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field

from services.ast_parser import FileEntities

logger = logging.getLogger(__name__)

# Spike threshold: complexity increase > 25% = spike
SPIKE_THRESHOLD = 0.25


# ---------------------------------------------------------------------------
# Radon-based complexity analysis
# ---------------------------------------------------------------------------

def _compute_radon_complexity(source: str, file_path: str) -> List[Dict]:
    """
    Compute cyclomatic complexity for all functions in a Python source file.

    Returns a list of dicts:
        [{"name": str, "complexity": float, "line_number": int}]

    Non-Python files return an empty list (no radon support).
    Radon complexity scale:
        1-5   : Simple, low risk
        6-10  : Moderate
        11-15 : High — review recommended
        16+   : Very high — refactoring strongly advised
    """
    if not file_path.endswith(".py"):
        return []

    try:
        from radon.complexity import cc_visit
        results = cc_visit(source)
        return [
            {
                "name": block.name,
                "complexity": float(block.complexity),
                "line_number": block.lineno,
                "file": file_path,
            }
            for block in results
        ]
    except SyntaxError:
        logger.debug(f"Syntax error in {file_path}, skipping radon")
        return []
    except ImportError:
        logger.warning("radon not installed — using complexity=1 fallback")
        return []
    except Exception as e:
        logger.debug(f"Radon failed on {file_path}: {e}")
        return []


def compute_commit_complexity(file_contents: dict) -> Tuple[float, List[Dict]]:
    """
    Compute the mean cyclomatic complexity across all changed files in a commit.

    Args:
        file_contents : dict mapping file_path → raw source text

    Returns:
        (mean_complexity, all_function_metrics)
        where all_function_metrics is a flat list of per-function dicts
    """
    all_functions = []

    for file_path, source in file_contents.items():
        functions = _compute_radon_complexity(source, file_path)
        all_functions.extend(functions)

    if not all_functions:
        # Fallback: count non-blank lines as a rough proxy for complexity
        total_lines = sum(
            len([l for l in src.splitlines() if l.strip()])
            for src in file_contents.values()
        )
        return max(1.0, float(total_lines) / 50.0), []

    mean_complexity = sum(f["complexity"] for f in all_functions) / len(all_functions)
    return mean_complexity, all_functions


# ---------------------------------------------------------------------------
# Coupling computation from dependency graph
# ---------------------------------------------------------------------------

def compute_coupling_from_graph(G) -> float:
    """
    Compute mean fan-out across all function and class nodes in the graph.

    Fan-out = number of outgoing edges (things this node calls/imports).
    High fan-out signals a module that is hard to test in isolation because
    it depends on many other modules.

    Args:
        G : networkx.DiGraph produced by graph_builder.build_graph()

    Returns:
        Mean fan-out as a float. 0.0 if the graph has no function/class nodes.
    """
    try:
        import networkx as nx
        # Only consider function and class nodes — file nodes inflate the metric
        function_nodes = [
            n for n, d in G.nodes(data=True)
            if d.get("kind") in {"function", "class"}
        ]
        if not function_nodes:
            return 0.0
        total_fanout = sum(G.out_degree(n) for n in function_nodes)
        return total_fanout / len(function_nodes)
    except Exception as e:
        logger.debug(f"Coupling computation failed: {e}")
        return 0.0


def compute_file_coupling(G, file_path: str) -> Tuple[int, int]:
    """
    Compute fan-in and fan-out for a specific file node in the graph.

    Returns:
        (fan_in, fan_out)
    """
    try:
        from services.graph_builder import file_node_id
        node_id = file_node_id(file_path)
        if node_id not in G:
            return 0, 0
        return G.in_degree(node_id), G.out_degree(node_id)
    except Exception:
        return 0, 0


# ---------------------------------------------------------------------------
# Churn risk
# ---------------------------------------------------------------------------

def compute_churn_risk(
    churn_count: int,
    max_churn: int,
    coupling_score: float,
    max_coupling: float,
) -> float:
    """
    Compute the churn-risk score for a file.

    Formula:
        risk = normalised_churn × normalised_coupling

    Both inputs are normalised to [0, 1] against the repo's max values
    to produce a comparable score across files.

    Args:
        churn_count   : Number of commits this file appeared in
        max_churn     : Maximum churn_count seen across all files in the repo
        coupling_score: Fan-out of this file's functions (mean)
        max_coupling  : Maximum coupling_score seen across all files

    Returns:
        Risk score in [0, 1]. 0 = safe, 1 = highest risk.
    """
    norm_churn = churn_count / max_churn if max_churn > 0 else 0.0
    norm_coupling = coupling_score / max_coupling if max_coupling > 0 else 0.0
    return norm_churn * norm_coupling


# ---------------------------------------------------------------------------
# Spike detection
# ---------------------------------------------------------------------------

def is_spike_commit(
    complexity_current: Optional[float],
    complexity_previous: Optional[float],
    threshold: float = SPIKE_THRESHOLD,
) -> bool:
    """
    Determine whether a commit represents a complexity spike.

    A spike is defined as complexity increasing by more than `threshold`
    percent relative to the previous commit. This is the gate for the
    cost-justified LLM Call 1 (spike explainer).

    Args:
        complexity_current  : Complexity score at this commit
        complexity_previous : Complexity score at the parent commit
        threshold           : Minimum relative increase to qualify (default 25%)

    Returns:
        True if the commit is a spike, False otherwise.
    """
    if complexity_current is None or complexity_previous is None:
        return False
    if complexity_previous == 0:
        return complexity_current > 5   # baseline spike if starting from 0
    delta = (complexity_current - complexity_previous) / complexity_previous
    return delta > threshold


def compute_complexity_delta(
    current: Optional[float],
    previous: Optional[float],
) -> Optional[float]:
    """
    Compute percentage change in complexity vs the previous commit.

    Returns None if either value is unavailable.
    Returns a percentage (e.g. 0.35 means +35%).
    """
    if current is None or previous is None:
        return None
    if previous == 0:
        return None
    return (current - previous) / previous


# ---------------------------------------------------------------------------
# Hotspot aggregation (called after all commits are processed)
# ---------------------------------------------------------------------------

def normalise_file_risks(
    file_risks: List[Dict],
) -> List[Dict]:
    """
    Normalise churn and coupling scores and compute composite risk_score.

    Called once after all commits are ingested, operating over the
    aggregated FileMetric rows.

    Args:
        file_risks : List of dicts:
            {"file_path", "churn_count", "coupling_score", "complexity_score"}

    Returns:
        Same list, each dict updated with "risk_score" in [0, 1]
    """
    if not file_risks:
        return file_risks

    max_churn = max(f["churn_count"] for f in file_risks) or 1
    max_coupling = max(f["coupling_score"] for f in file_risks) or 1
    max_complexity = max(f["complexity_score"] for f in file_risks) or 1

    for f in file_risks:
        nc = f["churn_count"] / max_churn
        nk = f["coupling_score"] / max_coupling
        nx = f["complexity_score"] / max_complexity
        # Weighted composite: churn is most predictive, then coupling
        f["risk_score"] = round(0.5 * nc + 0.3 * nk + 0.2 * nx, 4)

    return sorted(file_risks, key=lambda x: x["risk_score"], reverse=True)
