"""
routers/insights.py — LLM-powered insight endpoints.

Endpoints:
  GET /api/repos/{id}/commits/{sha}/spike-explanation → explain a complexity spike
  GET /api/repos/{id}/summary                         → architectural drift summary
  GET /api/repos/{id}/narrative                       → full repo health narrative

All three endpoints check the SQLite LLM cache before calling the API.
If a cached response exists (from a previous call), it is returned immediately
with `cached: true`. This enforces the cost constraint from the architecture doc.

LLM call budget per repo (maximum):
  - spike-explanation : 1 call per spike commit (~8–12 per 500-commit repo)
  - summary           : 1 call per repo (triggered post-ingestion)
  - narrative         : 1 call per repo (triggered post-ingestion)
"""

import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Commit, Repository, LLMCache, ArchitecturalSummary, RepoNarrative, FileMetric
from services.llm_service import generate_spike_explanation

router = APIRouter(prefix="/repos", tags=["insights"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class SpikeExplanationResponse(BaseModel):
    sha: str
    complexityBefore: Optional[float] = None
    complexityAfter: Optional[float] = None
    percentChange: Optional[float] = None
    explanation: str
    isIntentional: Optional[bool] = None
    recommendations: List[str] = []
    cached: bool


class ArchitecturalSummaryResponse(BaseModel):
    repoId: int
    summary: str
    keyTrends: List[str] = []
    riskModules: List[str] = []
    generatedAt: str
    cached: bool


class RepoNarrativeResponse(BaseModel):
    repoId: int
    narrative: str
    highlights: List[str] = []
    generatedAt: str
    cached: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_llm_cache(db: Session, repo_id: int, sha: Optional[str], kind: str) -> Optional[dict]:
    """Check if a cached LLM response exists. Returns the parsed JSON or None."""
    entry = (
        db.query(LLMCache)
        .filter(
            LLMCache.repo_id == repo_id,
            LLMCache.sha == sha,
            LLMCache.kind == kind,
        )
        .first()
    )
    if entry:
        try:
            return json.loads(entry.response_json)
        except Exception:
            return None
    return None


def _save_llm_cache(db: Session, repo_id: int, sha: Optional[str], kind: str, data: dict):
    """Persist an LLM response to the cache table."""
    entry = LLMCache(
        repo_id=repo_id,
        sha=sha,
        kind=kind,
        response_json=json.dumps(data),
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/{repo_id}/commits/{sha}/spike-explanation",
            response_model=SpikeExplanationResponse)
def get_spike_explanation(repo_id: int, sha: str, db: Session = Depends(get_db)):
    """
    Return an LLM explanation for why this commit caused a complexity spike.

    Returns 404 if this commit is not flagged as a spike commit.
    Returns cached response if one exists (avoids duplicate API calls).

    This is LLM Call 1 from the architecture document.
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

    if not commit.is_spike_commit:
        raise HTTPException(
            404,
            detail="This commit is not a complexity spike. No explanation available."
        )

    # Check cache
    cached = _get_llm_cache(db, repo_id, commit.sha, "spike")
    if cached:
        pct = None
        cb = cached.get("complexityBefore")
        ca = cached.get("complexityAfter")
        if cb and ca and cb > 0:
            pct = round((ca - cb) / cb * 100, 1)
        return SpikeExplanationResponse(
            sha=commit.sha,
            complexityBefore=cb,
            complexityAfter=ca,
            percentChange=pct,
            explanation=cached.get("explanation", ""),
            isIntentional=cached.get("isIntentional"),
            recommendations=cached.get("recommendations", []),
            cached=True,
        )

    # Get previous commit complexity
    prev_commit = (
        db.query(Commit)
        .filter(
            Commit.repo_id == repo_id,
            Commit.commit_index == commit.commit_index - 1,
        )
        .first()
    )
    complexity_before = prev_commit.complexity if prev_commit else None
    complexity_after = commit.complexity

    # Get changed files
    changed_files = []
    if commit.changed_files_json:
        try:
            changed_files = json.loads(commit.changed_files_json)
        except Exception:
            pass

    pct = None
    if complexity_before and complexity_before > 0 and complexity_after:
        pct = round((complexity_after - complexity_before) / complexity_before * 100, 1)

    # Generate via LLM (Call 1)
    result = generate_spike_explanation(
        sha=commit.sha,
        complexity_before=complexity_before,
        complexity_after=complexity_after,
        diff_text="",   # diff not stored — pass empty
        changed_files=changed_files[:10],
    )

    # Cache the result
    cache_data = {
        "complexityBefore": complexity_before,
        "complexityAfter": complexity_after,
        "explanation": result["explanation"],
        "isIntentional": result.get("is_intentional"),
        "recommendations": result.get("recommendations", []),
    }
    _save_llm_cache(db, repo_id, commit.sha, "spike", cache_data)

    return SpikeExplanationResponse(
        sha=commit.sha,
        complexityBefore=complexity_before,
        complexityAfter=complexity_after,
        percentChange=pct,
        explanation=result["explanation"],
        isIntentional=result.get("is_intentional"),
        recommendations=result.get("recommendations", []),
        cached=False,
    )


@router.get("/{repo_id}/summary", response_model=ArchitecturalSummaryResponse)
def get_architectural_summary(repo_id: int, db: Session = Depends(get_db)):
    """
    Return the architectural drift summary for the repository.

    This is generated during ingestion (LLM Call 2) and cached permanently.
    If the repo is still ingesting, returns a placeholder.
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(404, detail="Repository not found")

    summary = (
        db.query(ArchitecturalSummary)
        .filter(ArchitecturalSummary.repo_id == repo_id)
        .first()
    )

    if not summary:
        if repo.status in ("pending", "ingesting"):
            return ArchitecturalSummaryResponse(
                repoId=repo_id,
                summary="Analysis in progress. Check back when ingestion is complete.",
                keyTrends=[],
                riskModules=[],
                generatedAt=datetime.utcnow().isoformat() + "Z",
                cached=False,
            )
        raise HTTPException(404, detail="No architectural summary available yet.")

    key_trends = []
    if summary.key_trends:
        try:
            key_trends = json.loads(summary.key_trends)
        except Exception:
            pass

    risk_modules = []
    if summary.risk_modules:
        try:
            risk_modules = json.loads(summary.risk_modules)
        except Exception:
            pass

    return ArchitecturalSummaryResponse(
        repoId=repo_id,
        summary=summary.summary,
        keyTrends=key_trends,
        riskModules=risk_modules,
        generatedAt=summary.generated_at.isoformat() + "Z",
        cached=True,
    )


@router.get("/{repo_id}/narrative", response_model=RepoNarrativeResponse)
def get_repo_narrative(repo_id: int, db: Session = Depends(get_db)):
    """
    Return the one-time demo narrative for the repository health story.

    This is generated during ingestion (LLM Call 3) and cached permanently.
    If ingestion is still running, returns a placeholder message.
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(404, detail="Repository not found")

    narrative = (
        db.query(RepoNarrative)
        .filter(RepoNarrative.repo_id == repo_id)
        .first()
    )

    if not narrative:
        if repo.status in ("pending", "ingesting"):
            return RepoNarrativeResponse(
                repoId=repo_id,
                narrative="Narrative will be generated once ingestion is complete.",
                highlights=[],
                generatedAt=datetime.utcnow().isoformat() + "Z",
                cached=False,
            )
        raise HTTPException(404, detail="No narrative available yet.")

    highlights = []
    if narrative.highlights:
        try:
            highlights = json.loads(narrative.highlights)
        except Exception:
            pass

    return RepoNarrativeResponse(
        repoId=repo_id,
        narrative=narrative.narrative,
        highlights=highlights,
        generatedAt=narrative.generated_at.isoformat() + "Z",
        cached=True,
    )
