"""
routers/graph.py — Knowledge graph diff endpoints.

Endpoints:
  GET /api/repos/{id}/commits/{sha}/graph-diff

Returns the structural before/after graph diff for a specific commit.
The diff data was computed during ingestion (stored as JSON in the commits table)
and is served directly here — no computation on request.

Frontend renders this as an interactive force-directed graph where:
  - New nodes/edges are highlighted green (added)
  - Removed nodes/edges are highlighted red (removed)
  - Changed nodes are amber
  - Unchanged nodes are gray
"""

import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Commit, Repository

router = APIRouter(prefix="/repos", tags=["graph"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class GraphNode(BaseModel):
    id: str
    label: str
    kind: str          # file | function | class | module
    complexity: Optional[float] = None
    fanIn: Optional[int] = None
    fanOut: Optional[int] = None
    changeType: str    # added | removed | changed | unchanged


class GraphEdge(BaseModel):
    source: str
    target: str
    kind: str          # calls | imports | inherits
    changeType: str    # added | removed | unchanged


class GraphDiffResponse(BaseModel):
    sha: str
    parentSha: Optional[str] = None
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    addedNodes: int
    removedNodes: int
    changedNodes: int
    addedEdges: int
    removedEdges: int


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/{repo_id}/commits/{sha}/graph-diff", response_model=GraphDiffResponse)
def get_graph_diff(repo_id: int, sha: str, db: Session = Depends(get_db)):
    """
    Return the knowledge graph diff for a specific commit.

    The diff JSON was serialised during ingestion by graph_builder.serialize_graph_diff()
    and stored in the commits.graph_diff_json column. This endpoint just deserialises
    and returns it — no on-the-fly computation required.

    The response contains:
      - All nodes visible in either the before or after graph
      - All edges visible in either the before or after graph
      - changeType annotations for visual colouring in the frontend
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(404, detail="Repository not found")

    commit = (
        db.query(Commit)
        .filter(Commit.repo_id == repo_id, Commit.sha == sha)
        .first()
    )
    if not commit:
        commit = (
            db.query(Commit)
            .filter(Commit.repo_id == repo_id, Commit.short_sha == sha)
            .first()
        )
    if not commit:
        raise HTTPException(404, detail="Commit not found")

    # Deserialise the stored graph diff JSON
    if commit.graph_diff_json:
        try:
            diff_data = json.loads(commit.graph_diff_json)
        except json.JSONDecodeError:
            diff_data = {}
    else:
        diff_data = {}

    # Parse parent SHA from the previous commit
    parent_commit = (
        db.query(Commit)
        .filter(
            Commit.repo_id == repo_id,
            Commit.commit_index == commit.commit_index - 1,
        )
        .first()
    )
    parent_sha = parent_commit.sha if parent_commit else None

    # Build response — handle missing/empty diff gracefully
    raw_nodes = diff_data.get("nodes", [])
    raw_edges = diff_data.get("edges", [])

    nodes = [
        GraphNode(
            id=n.get("id", ""),
            label=n.get("label", n.get("id", "")),
            kind=n.get("kind", "file"),
            complexity=n.get("complexity"),
            fanIn=n.get("fanIn"),
            fanOut=n.get("fanOut"),
            changeType=n.get("changeType", "unchanged"),
        )
        for n in raw_nodes
        if n.get("id")  # skip malformed nodes
    ]

    edges = [
        GraphEdge(
            source=e.get("source", ""),
            target=e.get("target", ""),
            kind=e.get("kind", "calls"),
            changeType=e.get("changeType", "unchanged"),
        )
        for e in raw_edges
        if e.get("source") and e.get("target")
    ]

    return GraphDiffResponse(
        sha=commit.sha,
        parentSha=parent_sha,
        nodes=nodes,
        edges=edges,
        addedNodes=diff_data.get("addedNodes", 0),
        removedNodes=diff_data.get("removedNodes", 0),
        changedNodes=diff_data.get("changedNodes", 0),
        addedEdges=diff_data.get("addedEdges", 0),
        removedEdges=diff_data.get("removedEdges", 0),
    )
