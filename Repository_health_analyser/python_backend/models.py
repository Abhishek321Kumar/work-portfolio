"""
models.py — SQLAlchemy ORM table definitions.

Each class here maps to a SQLite table. SQLAlchemy creates the tables
automatically on startup via `Base.metadata.create_all(engine)`.

Tables:
  - repositories    : one row per ingested Git repo
  - commits         : one row per analysed commit (metrics stored here)
  - file_metrics    : per-file churn/coupling/complexity rolled up
  - llm_cache       : cached LLM responses keyed by (repo_id, sha, kind)
  - architectural_summaries : cached per-repo architectural summaries
  - repo_narratives : cached per-repo LLM narratives

Libraries:
  - sqlalchemy  : column types, relationships, indexes
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text,
    DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from database import Base


class Repository(Base):
    """
    One row per ingested Git repository.

    status:
      pending   — just created, ingestion not started
      ingesting — background worker is processing commits
      ready     — all commits processed successfully
      error     — ingestion failed (see error_message)
    """
    __tablename__ = "repositories"

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String(255), nullable=False)
    url            = Column(String(1024), nullable=False, unique=True)
    status         = Column(String(50), default="pending", nullable=False)
    total_commits  = Column(Integer, nullable=True)
    processed_commits = Column(Integer, default=0, nullable=True)
    error_message  = Column(Text, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at     = Column(DateTime, default=datetime.utcnow,
                            onupdate=datetime.utcnow, nullable=False)

    # Relationships
    commits        = relationship("Commit", back_populates="repository",
                                  cascade="all, delete-orphan")
    file_metrics   = relationship("FileMetric", back_populates="repository",
                                  cascade="all, delete-orphan")
    llm_cache      = relationship("LLMCache", back_populates="repository",
                                  cascade="all, delete-orphan")
    arch_summary   = relationship("ArchitecturalSummary",
                                  back_populates="repository",
                                  uselist=False,
                                  cascade="all, delete-orphan")
    narrative      = relationship("RepoNarrative",
                                  back_populates="repository",
                                  uselist=False,
                                  cascade="all, delete-orphan")


class Commit(Base):
    """
    One row per analysed commit, with all computed health metrics.

    complexity   — mean cyclomatic complexity across all changed functions
                   (computed by radon)
    coupling     — average fan-out across nodes in the commit's dependency graph
                   (computed by networkx analysis)
    churn_risk   — composite score: how_often_file_changes × coupling_score
    is_spike_commit — True when complexity jumped > SPIKE_THRESHOLD% vs parent
    graph_diff_json — serialised JSON blob of the NetworkX graph delta
                      (nodes added/removed/changed + edges)
    """
    __tablename__ = "commits"

    id                = Column(Integer, primary_key=True, index=True)
    repo_id           = Column(Integer, ForeignKey("repositories.id",
                               ondelete="CASCADE"), nullable=False)
    sha               = Column(String(40), nullable=False)
    short_sha         = Column(String(8), nullable=False)
    message           = Column(Text, nullable=False)
    author            = Column(String(255), nullable=False)
    timestamp         = Column(DateTime, nullable=False)
    commit_index      = Column(Integer, nullable=False)   # chronological order
    files_changed     = Column(Integer, nullable=True)
    lines_added       = Column(Integer, nullable=True)
    lines_removed     = Column(Integer, nullable=True)

    # Health metrics
    complexity        = Column(Float, nullable=True)
    coupling          = Column(Float, nullable=True)
    churn_risk        = Column(Float, nullable=True)
    complexity_delta  = Column(Float, nullable=True)  # diff vs parent
    coupling_delta    = Column(Float, nullable=True)
    is_spike_commit   = Column(Boolean, default=False, nullable=False)

    # Graph data (stored as JSON text)
    graph_diff_json   = Column(Text, nullable=True)
    # JSON list of {name, file, complexity, line_number}
    top_functions_json = Column(Text, nullable=True)
    # JSON list of changed file paths
    changed_files_json = Column(Text, nullable=True)

    repository = relationship("Repository", back_populates="commits")

    __table_args__ = (
        Index("ix_commits_repo_sha", "repo_id", "sha", unique=True),
        Index("ix_commits_repo_index", "repo_id", "commit_index"),
    )


class FileMetric(Base):
    """
    Rolled-up per-file metrics across all commits in a repo.

    churn_count     — number of commits that touched this file
    coupling_score  — average fan-out of this file's functions
    complexity_score — average cyclomatic complexity of functions in this file
    risk_score      — composite: normalised(churn) × normalised(coupling)
    """
    __tablename__ = "file_metrics"

    id               = Column(Integer, primary_key=True, index=True)
    repo_id          = Column(Integer, ForeignKey("repositories.id",
                              ondelete="CASCADE"), nullable=False)
    file_path        = Column(String(1024), nullable=False)
    churn_count      = Column(Integer, default=0, nullable=False)
    coupling_score   = Column(Float, default=0.0, nullable=False)
    complexity_score = Column(Float, default=0.0, nullable=False)
    risk_score       = Column(Float, default=0.0, nullable=False)
    last_changed_sha = Column(String(40), nullable=True)
    last_changed_at  = Column(DateTime, nullable=True)

    repository = relationship("Repository", back_populates="file_metrics")

    __table_args__ = (
        Index("ix_file_metrics_repo_path", "repo_id", "file_path", unique=True),
        Index("ix_file_metrics_risk", "repo_id", "risk_score"),
    )


class LLMCache(Base):
    """
    Caches LLM responses to avoid redundant API calls.

    kind: "spike" | "summary" | "narrative"
    When kind="spike", sha identifies the specific commit.
    """
    __tablename__ = "llm_cache"

    id           = Column(Integer, primary_key=True, index=True)
    repo_id      = Column(Integer, ForeignKey("repositories.id",
                          ondelete="CASCADE"), nullable=False)
    sha          = Column(String(40), nullable=True)    # NULL for repo-level
    kind         = Column(String(50), nullable=False)   # spike | summary | narrative
    response_json = Column(Text, nullable=False)        # cached JSON
    created_at   = Column(DateTime, default=datetime.utcnow)

    repository = relationship("Repository", back_populates="llm_cache")

    __table_args__ = (
        Index("ix_llm_cache_lookup", "repo_id", "sha", "kind"),
    )


class ArchitecturalSummary(Base):
    """
    Cached LLM architectural drift summary for a repository.
    Regenerated every 50 commits or when the user requests it.
    """
    __tablename__ = "architectural_summaries"

    id           = Column(Integer, primary_key=True, index=True)
    repo_id      = Column(Integer, ForeignKey("repositories.id",
                          ondelete="CASCADE"), nullable=False, unique=True)
    summary      = Column(Text, nullable=False)
    key_trends   = Column(Text, nullable=True)   # JSON list of strings
    risk_modules = Column(Text, nullable=True)   # JSON list of strings
    generated_at = Column(DateTime, default=datetime.utcnow)

    repository = relationship("Repository", back_populates="arch_summary")


class RepoNarrative(Base):
    """
    Cached LLM-generated full narrative walkthrough of repo health.
    Generated once per demo run (one-time call per constraint 1 / Call 3).
    """
    __tablename__ = "repo_narratives"

    id           = Column(Integer, primary_key=True, index=True)
    repo_id      = Column(Integer, ForeignKey("repositories.id",
                          ondelete="CASCADE"), nullable=False, unique=True)
    narrative    = Column(Text, nullable=False)
    highlights   = Column(Text, nullable=True)   # JSON list of strings
    generated_at = Column(DateTime, default=datetime.utcnow)

    repository = relationship("Repository", back_populates="narrative")
