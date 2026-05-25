"""
graph_builder.py — Knowledge graph construction and diffing using NetworkX.

What this module does:
  For each commit, build an in-memory directed graph where:
    Nodes = files, functions, and classes
    Edges = imports, function calls, and class inheritance

  Then compute the *delta* between two consecutive commit graphs:
    - Nodes/edges present in `after` but not `before` → ADDED (green)
    - Nodes/edges present in `before` but not `after` → REMOVED (red)
    - Nodes present in both but with changed attributes → CHANGED (amber)
    - Nodes/edges in both and unchanged → UNCHANGED (gray)

  The delta is stored as JSON and returned to the frontend as the
  `graph-diff` endpoint response.

Libraries:
  - networkx : Industry-standard Python graph library. Supports directed graphs,
               graph algorithms (degree, centrality), and set operations.
               All computation is in-memory — no database needed.

Design notes:
  "No Index" architecture: we do NOT store the full graph per commit.
  We build G_before and G_after in memory, compute the delta, store only
  the delta JSON, then let both graphs be garbage-collected.
  This reduces storage from O(commits × nodes) to O(commits × delta_nodes).
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from services.ast_parser import FileEntities, FunctionInfo, ClassInfo

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Node and Edge IDs
# ---------------------------------------------------------------------------

def file_node_id(file_path: str) -> str:
    """Unique ID for a file node."""
    return f"file:{file_path}"


def function_node_id(file_path: str, function_name: str) -> str:
    """Unique ID for a function node."""
    return f"func:{file_path}::{function_name}"


def class_node_id(file_path: str, class_name: str) -> str:
    """Unique ID for a class node."""
    return f"class:{file_path}::{class_name}"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph(entities_list: List[FileEntities]) -> nx.DiGraph:
    """
    Build a NetworkX directed graph from a list of parsed file entities.

    Node attributes:
        label      : Human-readable display name
        kind       : "file" | "function" | "class"
        complexity : Cyclomatic complexity (set later by metrics_engine)
        file_path  : Path of the source file

    Edge attributes:
        kind       : "imports" | "calls" | "inherits"

    Args:
        entities_list : Output of ast_parser.parse_changed_files()

    Returns:
        Directed graph (nx.DiGraph)
    """
    G = nx.DiGraph()

    for entities in entities_list:
        file_id = file_node_id(entities.file_path)

        # File node
        G.add_node(file_id, label=entities.file_path, kind="file",
                   complexity=0.0, file_path=entities.file_path)

        # Function nodes
        for fn in entities.functions:
            fn_id = function_node_id(fn.file_path, fn.name)
            G.add_node(fn_id, label=fn.name, kind="function",
                       complexity=fn.complexity, file_path=fn.file_path,
                       line_number=fn.line_number)
            # Edge: file → function (containment)
            G.add_edge(file_id, fn_id, kind="contains")

        # Class nodes
        for cls in entities.classes:
            cls_id = class_node_id(cls.file_path, cls.name)
            G.add_node(cls_id, label=cls.name, kind="class",
                       complexity=0.0, file_path=cls.file_path,
                       line_number=cls.line_number)
            G.add_edge(file_id, cls_id, kind="contains")

            # Inheritance edges (approximation — base may be in another file)
            for base in cls.bases:
                # Try to find base class node in current graph
                base_id = None
                for node_id, attrs in G.nodes(data=True):
                    if attrs.get("kind") == "class" and attrs.get("label") == base:
                        base_id = node_id
                        break
                if base_id:
                    G.add_edge(cls_id, base_id, kind="inherits")

        # Import edges (file-level dependency)
        for imp in entities.imports:
            # Try to find the imported file node
            for node_id, attrs in G.nodes(data=True):
                if attrs.get("kind") == "file":
                    # Rough match: module name appears in file path
                    if imp.imported_module in attrs.get("file_path", ""):
                        G.add_edge(file_id, node_id, kind="imports")
                        break
            # Also add a virtual import node if target not found
            # (for external libraries)

        # Call edges
        for call in entities.calls:
            caller_id = function_node_id(call.caller_file, call.caller_function)
            # Search for callee anywhere in the graph
            callee_id = None
            for node_id, attrs in G.nodes(data=True):
                if attrs.get("kind") == "function" and attrs.get("label") == call.callee_name:
                    callee_id = node_id
                    break
            if callee_id and caller_id in G:
                G.add_edge(caller_id, callee_id, kind="calls")

    return G


def compute_graph_metrics(G: nx.DiGraph) -> Dict[str, Dict]:
    """
    Compute fan-in and fan-out for every node in the graph.

    fan_out = out-degree (how many things this node calls/imports)
    fan_in  = in-degree (how many things call/import this node)

    High fan-in = widely depended-upon (changing this breaks a lot)
    High fan-out = complex dependency web (hard to test in isolation)

    Returns:
        dict mapping node_id → {"fan_in": int, "fan_out": int}
    """
    metrics = {}
    for node in G.nodes():
        metrics[node] = {
            "fan_in": G.in_degree(node),
            "fan_out": G.out_degree(node),
        }
    return metrics


# ---------------------------------------------------------------------------
# Graph diffing
# ---------------------------------------------------------------------------

@dataclass
class GraphDelta:
    """
    The structural difference between two consecutive commit graphs.

    Used to populate the GraphDiff API response and the graph diff visualizer.
    """
    nodes_before: Set[str] = field(default_factory=set)
    nodes_after: Set[str] = field(default_factory=set)
    edges_before: Set[Tuple[str, str, str]] = field(default_factory=set)
    edges_after: Set[Tuple[str, str, str]] = field(default_factory=set)

    @property
    def added_nodes(self) -> Set[str]:
        return self.nodes_after - self.nodes_before

    @property
    def removed_nodes(self) -> Set[str]:
        return self.nodes_before - self.nodes_after

    @property
    def unchanged_nodes(self) -> Set[str]:
        return self.nodes_before & self.nodes_after

    @property
    def added_edges(self) -> Set[Tuple]:
        return self.edges_after - self.edges_before

    @property
    def removed_edges(self) -> Set[Tuple]:
        return self.edges_before - self.edges_after


def diff_graphs(G_before: nx.DiGraph, G_after: nx.DiGraph) -> GraphDelta:
    """
    Compute the structural delta between two graph snapshots.

    Args:
        G_before : Graph at the parent commit
        G_after  : Graph at the current commit

    Returns:
        GraphDelta describing what was added, removed, and unchanged
    """
    nodes_before = set(G_before.nodes())
    nodes_after = set(G_after.nodes())

    def edge_set(G: nx.DiGraph) -> Set[Tuple[str, str, str]]:
        return {(u, v, data.get("kind", "")) for u, v, data in G.edges(data=True)}

    return GraphDelta(
        nodes_before=nodes_before,
        nodes_after=nodes_after,
        edges_before=edge_set(G_before),
        edges_after=edge_set(G_after),
    )


def serialize_graph_diff(
    delta: GraphDelta,
    G_before: nx.DiGraph,
    G_after: nx.DiGraph,
) -> str:
    """
    Serialize a GraphDelta to JSON for storage and API responses.

    Returns a JSON string compatible with the GraphDiff API schema:
        {
          "nodes": [{"id", "label", "kind", "changeType", ...}],
          "edges": [{"source", "target", "kind", "changeType"}],
          "addedNodes": int, ...
        }
    """
    nodes_out = []

    # Combine all node IDs from both snapshots
    all_node_ids = delta.nodes_before | delta.nodes_after

    for node_id in all_node_ids:
        if node_id in delta.added_nodes:
            change_type = "added"
            attrs = G_after.nodes[node_id]
        elif node_id in delta.removed_nodes:
            change_type = "removed"
            attrs = G_before.nodes[node_id]
        else:
            change_type = "unchanged"
            attrs = G_after.nodes[node_id]

        nodes_out.append({
            "id": node_id,
            "label": attrs.get("label", node_id),
            "kind": attrs.get("kind", "file"),
            "complexity": attrs.get("complexity", 0),
            "fanIn": G_after.in_degree(node_id) if node_id in G_after else 0,
            "fanOut": G_after.out_degree(node_id) if node_id in G_after else 0,
            "changeType": change_type,
        })

    edges_out = []

    all_edges = delta.edges_before | delta.edges_after
    for (source, target, kind) in all_edges:
        if (source, target, kind) in delta.added_edges:
            change_type = "added"
        elif (source, target, kind) in delta.removed_edges:
            change_type = "removed"
        else:
            change_type = "unchanged"

        edges_out.append({
            "source": source,
            "target": target,
            "kind": kind,
            "changeType": change_type,
        })

    result = {
        "nodes": nodes_out,
        "edges": edges_out,
        "addedNodes": len(delta.added_nodes),
        "removedNodes": len(delta.removed_nodes),
        "changedNodes": 0,   # structural change tracking could be added here
        "addedEdges": len(delta.added_edges),
        "removedEdges": len(delta.removed_edges),
    }
    return json.dumps(result)
