"""
ingestion_task.py — Background ingestion worker.

This module runs the full ingestion pipeline for a single repository
in a background thread (via Python's threading module).

Pipeline steps (per commit):
  1. git_ingestion   : Clone the repo, walk commits, extract diffs
  2. ast_parser      : Parse changed files → entities (functions, classes, imports)
  3. graph_builder   : Build graph, diff with previous commit's graph
  4. metrics_engine  : Compute complexity (radon), coupling (networkx), churn risk

After all commits are processed:
  5. Normalise file risk scores (churn × coupling across entire repo)
  6. Trigger architectural summary generation (LLM Call 2)
  7. Trigger demo narrative generation (LLM Call 3)

Design notes:
  - Uses threading (not asyncio) because the git/radon/networkx operations are
    CPU-bound and blocking. Launching in a daemon thread lets FastAPI continue
    serving requests while ingestion runs.
  - The thread updates the Repository.status and Repository.processed_commits
    columns periodically so the frontend can poll /repos/{id}/status.
  - Errors are caught at the top level and stored in Repository.error_message.
"""

import json
import logging
import threading
from datetime import datetime
from typing import Optional

import networkx as nx

from database import SessionLocal
from models import Repository, Commit, FileMetric, ArchitecturalSummary, RepoNarrative
from services.git_ingestion import ingest_repository
from services.ast_parser import parse_changed_files
from services.graph_builder import build_graph, diff_graphs, serialize_graph_diff
from services.metrics_engine import (
    compute_commit_complexity,
    compute_coupling_from_graph,
    is_spike_commit,
    compute_complexity_delta,
    normalise_file_risks,
)
from services.llm_service import (
    generate_architectural_summary,
    generate_repo_narrative,
)

logger = logging.getLogger(__name__)


def _run_ingestion(repo_id: int, url: str, max_commits: int = 500):
    """
    Full ingestion pipeline for one repository. Runs in a background thread.

    Args:
        repo_id     : Database ID of the Repository row to update
        url         : HTTPS Git URL to clone and analyse
        max_commits : Maximum commits to process
    """
    db = SessionLocal()
    try:
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            logger.error(f"Repository {repo_id} not found in DB")
            return

        repo.status = "ingesting"
        repo.updated_at = datetime.utcnow()
        db.commit()

        # Track per-file metrics for hotspot computation
        file_churn: dict = {}           # file_path → churn_count
        file_coupling: dict = {}        # file_path → cumulative coupling_score
        file_complexity: dict = {}      # file_path → cumulative complexity
        file_last_sha: dict = {}        # file_path → last commit sha
        file_last_at: dict = {}         # file_path → last commit timestamp

        # Track previous complexity for spike detection
        prev_complexity: Optional[float] = None

        # Previous graph for diff computation
        prev_graph = nx.DiGraph()

        # Spike commits list for narrative
        spike_commits = []
        peak_spike = None
        peak_spike_delta = 0.0

        # Complexity time-series for architectural summary
        complexity_trend = []

        total_commits = 0

        def progress_callback(processed: int, total: int):
            nonlocal total_commits
            total_commits = total
            # Update DB every 10 commits for progress tracking
            if processed % 10 == 0 or processed == total:
                try:
                    db_inner = SessionLocal()
                    r = db_inner.query(Repository).filter(Repository.id == repo_id).first()
                    if r:
                        r.total_commits = total
                        r.processed_commits = processed
                        r.updated_at = datetime.utcnow()
                        db_inner.commit()
                    db_inner.close()
                except Exception as e:
                    logger.warning(f"Progress update failed: {e}")

        # -----------------------------------------------------------------------
        # Main commit walk
        # -----------------------------------------------------------------------
        for commit_info in ingest_repository(url, max_commits=max_commits,
                                             progress_callback=progress_callback):
            # Parse changed files into entities
            entities = parse_changed_files(commit_info.file_contents)

            # Build graph for this commit's changed files
            current_graph = build_graph(entities)

            # Compute complexity
            complexity, all_functions = compute_commit_complexity(
                commit_info.file_contents
            )

            # Compute coupling from graph
            coupling = compute_coupling_from_graph(current_graph)

            # Spike detection
            spike = is_spike_commit(complexity, prev_complexity)
            complexity_delta = compute_complexity_delta(complexity, prev_complexity)

            # Graph diff vs previous commit's graph
            graph_delta = diff_graphs(prev_graph, current_graph)
            graph_diff_json = serialize_graph_diff(graph_delta, prev_graph, current_graph)

            # Top 5 complex functions
            top_functions = sorted(
                all_functions, key=lambda x: x["complexity"], reverse=True
            )[:5]

            # Changed file paths
            changed_files = [f.path for f in commit_info.files]

            # Churn risk (will be normalised after all commits are processed)
            churn_risk = float(len(commit_info.files)) * coupling

            # Store commit in DB
            commit_row = Commit(
                repo_id=repo_id,
                sha=commit_info.sha,
                short_sha=commit_info.short_sha,
                message=commit_info.message,
                author=commit_info.author,
                timestamp=commit_info.timestamp,
                commit_index=commit_info.commit_index,
                files_changed=len(commit_info.files),
                lines_added=commit_info.total_added,
                lines_removed=commit_info.total_removed,
                complexity=round(complexity, 3),
                coupling=round(coupling, 3),
                churn_risk=round(churn_risk, 3),
                complexity_delta=round(complexity_delta, 4) if complexity_delta else None,
                coupling_delta=None,
                is_spike_commit=spike,
                graph_diff_json=graph_diff_json,
                top_functions_json=json.dumps(top_functions),
                changed_files_json=json.dumps(changed_files),
            )
            db.add(commit_row)

            # Update per-file metrics
            for fd in commit_info.files:
                fp = fd.path
                file_churn[fp] = file_churn.get(fp, 0) + 1
                file_last_sha[fp] = commit_info.sha
                file_last_at[fp] = commit_info.timestamp

                # Coupling: use graph coupling for this file
                from services.graph_builder import file_node_id
                node_id = file_node_id(fp)
                fan_out = current_graph.out_degree(node_id) if node_id in current_graph else 0
                file_coupling[fp] = file_coupling.get(fp, 0) + fan_out

                # Complexity: look for this file in all_functions
                file_fn_complexities = [
                    f["complexity"] for f in all_functions if f.get("file") == fp
                ]
                if file_fn_complexities:
                    file_complexity[fp] = max(
                        file_complexity.get(fp, 0),
                        sum(file_fn_complexities) / len(file_fn_complexities)
                    )

            # Track for LLM context
            if spike:
                spike_commits.append({
                    "sha": commit_info.sha,
                    "message": commit_info.message,
                    "delta": complexity_delta,
                })
                if (complexity_delta or 0) > peak_spike_delta:
                    peak_spike_delta = complexity_delta or 0
                    peak_spike = commit_row

            complexity_trend.append(complexity)
            prev_complexity = complexity
            prev_graph = current_graph

            # Batch commit every 50 rows to avoid large transactions
            if commit_info.commit_index % 50 == 0:
                db.commit()

        # Final DB flush for commits
        db.commit()

        # -----------------------------------------------------------------------
        # Post-ingestion: normalise file risk scores and store FileMetric rows
        # -----------------------------------------------------------------------
        file_risk_input = [
            {
                "file_path": fp,
                "churn_count": file_churn.get(fp, 1),
                "coupling_score": file_coupling.get(fp, 0.0),
                "complexity_score": file_complexity.get(fp, 0.0),
            }
            for fp in file_churn.keys()
        ]
        normalised = normalise_file_risks(file_risk_input)

        for fr in normalised:
            fm_row = FileMetric(
                repo_id=repo_id,
                file_path=fr["file_path"],
                churn_count=fr["churn_count"],
                coupling_score=round(fr["coupling_score"], 3),
                complexity_score=round(fr["complexity_score"], 3),
                risk_score=fr["risk_score"],
                last_changed_sha=file_last_sha.get(fr["file_path"]),
                last_changed_at=file_last_at.get(fr["file_path"]),
            )
            db.add(fm_row)
        db.commit()

        # -----------------------------------------------------------------------
        # LLM Call 2: Architectural drift summary
        # -----------------------------------------------------------------------
        top_hotspots = normalised[:5]
        arch_data = generate_architectural_summary(
            repo_name=repo.name,
            total_commits=len(complexity_trend),
            spike_count=len(spike_commits),
            top_hotspots=top_hotspots,
            avg_complexity_trend=complexity_trend,
        )
        arch_row = ArchitecturalSummary(
            repo_id=repo_id,
            summary=arch_data["summary"],
            key_trends=json.dumps(arch_data["key_trends"]),
            risk_modules=json.dumps(arch_data["risk_modules"]),
            generated_at=datetime.utcnow(),
        )
        db.add(arch_row)

        # -----------------------------------------------------------------------
        # LLM Call 3: Demo narrative
        # -----------------------------------------------------------------------
        current_complexity = complexity_trend[-1] if complexity_trend else 0.0
        top_file_paths = [fr["file_path"] for fr in normalised[:3]]

        narrative_data = generate_repo_narrative(
            repo_name=repo.name,
            total_commits=len(complexity_trend),
            spike_commits=spike_commits,
            peak_complexity_commit=(
                {"sha": peak_spike.sha, "message": peak_spike.message}
                if peak_spike else None
            ),
            current_avg_complexity=current_complexity,
            top_risky_files=top_file_paths,
        )
        narrative_row = RepoNarrative(
            repo_id=repo_id,
            narrative=narrative_data["narrative"],
            highlights=json.dumps(narrative_data["highlights"]),
            generated_at=datetime.utcnow(),
        )
        db.add(narrative_row)

        # -----------------------------------------------------------------------
        # Mark repository as ready
        # -----------------------------------------------------------------------
        repo.status = "ready"
        repo.total_commits = len(complexity_trend)
        repo.processed_commits = len(complexity_trend)
        repo.updated_at = datetime.utcnow()
        db.commit()

        logger.info(
            f"Ingestion complete for repo {repo_id}: "
            f"{len(complexity_trend)} commits, {len(spike_commits)} spikes"
        )

    except Exception as e:
        logger.error(f"Ingestion failed for repo {repo_id}: {e}", exc_info=True)
        try:
            repo = db.query(Repository).filter(Repository.id == repo_id).first()
            if repo:
                repo.status = "error"
                repo.error_message = str(e)[:500]
                repo.updated_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def start_ingestion(repo_id: int, url: str, max_commits: int = 500):
    """
    Launch the ingestion pipeline as a background daemon thread.

    FastAPI continues serving requests while ingestion runs.
    The thread updates Repository.status and Repository.processed_commits
    so the frontend can poll /repos/{id}/status for progress.

    Args:
        repo_id     : Database ID of the Repository row
        url         : HTTPS Git URL to clone
        max_commits : Maximum number of commits to process
    """
    thread = threading.Thread(
        target=_run_ingestion,
        args=(repo_id, url, max_commits),
        daemon=True,
        name=f"ingest-repo-{repo_id}",
    )
    thread.start()
    logger.info(f"Ingestion thread started for repo {repo_id} ({url})")
    return thread
