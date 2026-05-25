"""
main.py — FastAPI application entry point for RepoHealth.

This file wires together:
  - FastAPI app with CORS middleware (allows React frontend on any origin)
  - SQLite database initialisation (creates tables if they don't exist)
  - Route registration for all API modules:
      /api/healthz               → health check
      /api/repos/...             → repository management (repos.py)
      /api/repos/.../timeline    → metrics time-series (metrics.py)
      /api/repos/.../hotspots    → hotspot heatmap (metrics.py)
      /api/repos/.../graph-diff  → knowledge graph (graph.py)
      /api/repos/.../summary     → LLM summaries (insights.py)

How to run (development):
  cd python_backend
  uvicorn main:app --host 0.0.0.0 --port 8080 --reload

How to run (VS Code):
  1. Create a virtual environment: python -m venv .venv
  2. Activate: source .venv/bin/activate  (Linux/Mac)
               .venv\\Scripts\\activate    (Windows)
  3. Install deps: pip install -r requirements.txt
  4. Start server: uvicorn main:app --host 0.0.0.0 --port 8080 --reload
  5. API docs at: http://localhost:8080/api/docs

Environment variables:
  PORT          : Server port (default 8080, set by Replit workflow)
  DATABASE_URL  : SQLite path (default: ./repo_health.db)
  OPENAI_API_KEY: Required only for LLM features (spike explanations, summaries)

Architecture:
  The server mounts all routes under the /api prefix to match the Replit
  proxy configuration which routes /api/* to this service.
  React frontend calls /api/repos, /api/repos/{id}/timeline, etc.
"""

import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from routers import repos, metrics, graph, insights

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="RepoHealth API",
    description=(
        "Git repository health analysis. "
        "Ingests repos, computes code complexity/coupling metrics, "
        "builds knowledge graphs, and provides LLM-powered insights."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS — allow the React frontend (any origin in development)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Database initialisation
# ---------------------------------------------------------------------------
@app.on_event("startup")
def startup_event():
    """
    Create all database tables on startup if they don't already exist.
    SQLAlchemy inspects the ORM models in models.py and generates CREATE TABLE
    statements for any missing tables. Existing tables are left unchanged.
    """
    logger.info("Initialising database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database ready.")


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------
# All routers use prefix="/repos" internally; we mount them under /api so
# the final paths are /api/repos, /api/repos/{id}/timeline, etc.

app.include_router(repos.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(insights.router, prefix="/api")


# ---------------------------------------------------------------------------
# Health check (matches the OpenAPI spec's /api/healthz endpoint)
# ---------------------------------------------------------------------------
@app.get("/api/healthz", tags=["health"])
def health_check():
    """Standard health check used by the Replit proxy to verify the service is up."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Entry point for direct execution
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
