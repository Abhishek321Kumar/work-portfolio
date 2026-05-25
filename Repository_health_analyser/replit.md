# RepoHealth

A full-stack codebase observatory — ingests public Git repositories, computes complexity/coupling/churn metrics per commit, builds knowledge graphs, and visualises code health over time. Engineers use it to connect "this PR merged" to "here's how it shifted architecture and risk."

## Run & Operate

- Python API: starts automatically via the `artifacts/api-server` workflow (uvicorn on port 8080)
- React frontend: starts automatically via the `artifacts/repo-health` workflow (Vite on port 19574)
- `pnpm --filter @workspace/api-spec run codegen` — regenerate React Query hooks from OpenAPI spec
- See `python_backend/README_VSCODE.md` for full VS Code setup guide

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- **Backend**: Python 3.11 + FastAPI + uvicorn + SQLAlchemy (SQLite)
- **Analysis**: GitPython (git walking), radon (cyclomatic complexity), networkx (dependency graph)
- **LLM**: OpenAI gpt-4o-mini (spike explainer, architectural summary, narrative)
- **Frontend**: React + Vite + Recharts (timeline charts) + wouter (routing)
- **API layer**: OpenAPI → Orval codegen → typed React Query hooks

## Where things live

- `python_backend/`              — FastAPI backend (entry: `main.py`)
- `python_backend/services/`     — git ingestion, AST parsing, graph building, metrics, LLM
- `python_backend/routers/`      — FastAPI route handlers (repos, metrics, graph, insights)
- `python_backend/background/`   — threading-based background ingestion worker
- `python_backend/models.py`     — SQLAlchemy ORM (repos, commits, file_metrics, llm_cache)
- `artifacts/repo-health/src/`   — React frontend
- `artifacts/repo-health/src/pages/` — home, repo-overview, commits, commit-detail, hotspots, insights
- `lib/api-spec/openapi.yaml`    — source of truth for all API contracts
- `lib/api-client-react/src/generated/` — generated React Query hooks (do not edit)
- `lib/api-zod/src/generated/`   — generated Zod schemas (do not edit)

## Architecture decisions

- **SQLite not PostgreSQL**: RepoHealth uses its own SQLite DB (`python_backend/repo_health.db`) isolated from the workspace's shared Postgres. Zero config, ideal for per-repo analysis data.
- **"No Index" graph architecture**: We build G_before and G_after in memory per commit, compute the delta JSON, store only the delta — not the full graph snapshot. Reduces storage from O(commits×nodes) to O(commits×delta_nodes).
- **Cost-justified LLM calls**: Only 3 LLM calls per repo: (1) spike explainer per anomalous commit (~8-12 total), (2) architectural drift summary once post-ingestion, (3) demo narrative once. All cached in SQLite.
- **Background ingestion via threading**: Python `threading.Thread` (not asyncio) because git/radon operations are CPU-bound. FastAPI continues serving while ingestion runs.
- **Contract-first API**: OpenAPI spec → Orval codegen → typed hooks. Frontend never writes raw `fetch` calls.

## Product

- **Ingest any public GitHub repo** via HTTPS URL. Analyses up to 500 commits.
- **Health timeline**: Line chart of complexity + coupling over every commit. Spike commits flagged.
- **Commit explorer**: Full commit list with health metrics. Click any commit for detail view.
- **Commit detail**: Metric deltas vs parent, changed files, top complex functions, SVG force-directed knowledge graph diff (added=cyan, removed=red, unchanged=gray).
- **Hotspot heatmap**: Color-coded grid + ranked table showing files by composite risk score (churn × coupling × complexity). Hover tooltips with per-file breakdown.
- **LLM insights**: Architectural drift summary, spike explanations per anomalous commit, full repo health narrative.

## User preferences

- Always dark mode (cockpit aesthetic — deep blue-gray + cyan primary)
- Dense information display — engineer tool, not a marketing site
- No emojis in UI

## Gotchas

- Python packages install to `.pythonlibs/` (Replit's managed Python env, no venv needed)
- `DATABASE_URL` env var in the workspace points to Postgres for other services — RepoHealth ignores it and uses `REPO_HEALTH_DB` (or defaults to `python_backend/repo_health.db`)
- The API server artifact.toml runs `cd /home/runner/workspace/python_backend && uvicorn main:app ...` with absolute path because workflow cwd is the artifact dir
- `OPENAI_API_KEY` env var required for LLM features — app degrades gracefully without it
- Large repos (1000+ commits) should use `maxCommits: 200-300` for faster analysis

## Pointers

- `python_backend/README_VSCODE.md` — comprehensive VS Code setup guide with architecture diagrams
- See the `pnpm-workspace` skill for workspace structure details
