"""
routers/repos.py — Repository management endpoints.

Endpoints:
  GET  /api/repos          → list all repositories
  POST /api/repos          → ingest a new repository (async, starts background job)
  GET  /api/repos/{id}     → get single repository details
  DELETE /api/repos/{id}   → delete repository and all its data
  GET  /api/repos/{id}/status → poll ingestion progress

The POST /repos endpoint returns immediately with status="pending" and
launches a background thread. The frontend polls /repos/{id}/status
until status="ready" or status="error".
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from database import get_db
from models import Repository
from background.ingestion_task import start_ingestion

router = APIRouter(prefix="/repos", tags=["repos"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class RepoInput(BaseModel):
    """Request body for POST /repos."""
    url: str
    name: Optional[str] = None
    maxCommits: Optional[int] = 500


class RepoResponse(BaseModel):
    """Response shape for a single repository."""
    id: int
    name: str
    url: str
    status: str
    totalCommits: Optional[int] = None
    processedCommits: Optional[int] = None
    errorMessage: Optional[str] = None
    createdAt: str
    updatedAt: str

    class Config:
        from_attributes = True


class RepoStatusResponse(BaseModel):
    """Response for the /status polling endpoint."""
    repoId: int
    status: str
    totalCommits: Optional[int] = None
    processedCommits: Optional[int] = None
    progressPercent: Optional[float] = None
    currentSha: Optional[str] = None
    errorMessage: Optional[str] = None


def _repo_to_response(repo: Repository) -> RepoResponse:
    """Convert an ORM Repository to the API response shape."""
    return RepoResponse(
        id=repo.id,
        name=repo.name,
        url=repo.url,
        status=repo.status,
        totalCommits=repo.total_commits,
        processedCommits=repo.processed_commits,
        errorMessage=repo.error_message,
        createdAt=repo.created_at.isoformat() + "Z",
        updatedAt=repo.updated_at.isoformat() + "Z",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=List[RepoResponse])
def list_repos(db: Session = Depends(get_db)):
    """
    Return all repositories sorted by creation date (newest first).
    """
    repos = (
        db.query(Repository)
        .order_by(Repository.created_at.desc())
        .all()
    )
    return [_repo_to_response(r) for r in repos]


@router.post("", status_code=202)
def ingest_repo(body: RepoInput, db: Session = Depends(get_db)):
    """
    Create a repository record and start background ingestion.

    Returns immediately with status="pending". Poll /repos/{id}/status
    for progress updates.

    Validation:
      - URL must be a non-empty string (basic check)
      - Duplicate URLs return the existing repository record
    """
    url = str(body.url).strip()
    if not url or not url.startswith("http"):
        raise HTTPException(400, detail="Invalid repository URL. Must start with http(s).")

    # Check for duplicate
    existing = db.query(Repository).filter(Repository.url == url).first()
    if existing:
        # Re-trigger ingestion if it previously errored
        if existing.status == "error":
            existing.status = "pending"
            existing.error_message = None
            existing.updated_at = datetime.utcnow()
            db.commit()
            start_ingestion(existing.id, url, max_commits=body.maxCommits or 500)
        return _repo_to_response(existing)

    # Derive display name from URL if not provided
    name = body.name or url.rstrip("/").split("/")[-1].replace(".git", "")

    repo = Repository(
        name=name,
        url=url,
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    # Launch background ingestion thread
    start_ingestion(repo.id, url, max_commits=body.maxCommits or 500)

    return _repo_to_response(repo)


@router.get("/{repo_id}", response_model=RepoResponse)
def get_repo(repo_id: int, db: Session = Depends(get_db)):
    """Return a single repository by ID."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(404, detail="Repository not found")
    return _repo_to_response(repo)


@router.delete("/{repo_id}", status_code=204)
def delete_repo(repo_id: int, db: Session = Depends(get_db)):
    """
    Delete a repository and all its associated data.
    Cascade delete removes commits, file_metrics, llm_cache rows automatically.
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(404, detail="Repository not found")
    db.delete(repo)
    db.commit()
    return None


@router.get("/{repo_id}/status", response_model=RepoStatusResponse)
def get_repo_status(repo_id: int, db: Session = Depends(get_db)):
    """
    Poll ingestion progress.

    progressPercent is 0–100.0, derived from processedCommits / totalCommits.
    The frontend polls this endpoint every 3 seconds while status="ingesting".
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(404, detail="Repository not found")

    progress = None
    if repo.total_commits and repo.total_commits > 0 and repo.processed_commits is not None:
        progress = round(repo.processed_commits / repo.total_commits * 100, 1)

    return RepoStatusResponse(
        repoId=repo.id,
        status=repo.status,
        totalCommits=repo.total_commits,
        processedCommits=repo.processed_commits,
        progressPercent=progress,
        errorMessage=repo.error_message,
    )
