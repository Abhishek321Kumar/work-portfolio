# RepoHealth — VS Code Setup Guide

## What This App Does

RepoHealth is a full-stack codebase observatory. It ingests a public Git repository, 
analyses every commit using static analysis tools, builds a code knowledge graph, 
and visualises how repository health changes over time. 

Engineers can answer: "Which PR caused this complexity spike? Which files are architectural time bombs?"

---

## Project Architecture

```
┌──────────────────────────────────────────────────────┐
│  React Frontend (Vite + Recharts + React Force Graph) │
│  artifacts/repo-health/src/                           │
│  Serves at: http://localhost:PORT/                    │
└──────────────────────┬───────────────────────────────┘
                       │ HTTP calls to /api/*
┌──────────────────────▼───────────────────────────────┐
│  Python FastAPI Backend                               │
│  python_backend/main.py                              │
│  Serves at: http://localhost:8080/api/               │
└──────────────────────┬───────────────────────────────┘
                       │
       ┌───────────────┼────────────────────┐
       ▼               ▼                    ▼
  ┌─────────┐   ┌────────────┐    ┌─────────────────┐
  │ SQLite  │   │  GitPython │    │  OpenAI API     │
  │  DB     │   │  (clone &  │    │  (optional)     │
  │ metrics │   │  walk repo)│    │  LLM insights   │
  └─────────┘   └────────────┘    └─────────────────┘
```

---

## Python Backend Modules

### `main.py`
FastAPI app entry point. Registers all routers, sets up CORS, and creates 
SQLite tables on startup. Run this file with uvicorn.

Key libraries:
- `fastapi` : Modern async Python web framework. Auto-generates OpenAPI docs.
- `uvicorn` : ASGI server that runs FastAPI. Supports hot-reload with `--reload`.
- `pydantic` : Data validation. All request/response bodies are Pydantic models.

### `database.py`
SQLite database setup using SQLAlchemy ORM.

Key libraries:
- `sqlalchemy` : Python ORM. Maps Python classes to database tables.
- `sqlite3`    : Embedded DB, ships with Python — no server needed.

### `models.py`
ORM table definitions. Each class = one database table:
- `Repository`         : One row per ingested Git repo
- `Commit`             : One row per analysed commit (stores all metrics)
- `FileMetric`         : Per-file churn/coupling rolled up across all commits
- `LLMCache`           : Cached LLM responses (avoids duplicate API calls)
- `ArchitecturalSummary` : Per-repo LLM architectural drift summary
- `RepoNarrative`      : Per-repo LLM health story narrative

### `services/git_ingestion.py`
Git repository walking using GitPython.

Key libraries:
- `gitpython` (import: `git`) : Pure-Python Git client. Clones repos, walks 
  commits, extracts diffs (which files changed, lines added/removed).

How it works:
1. `clone_repo(url, target_dir)` : HTTPS clone into a temp directory
2. `walk_commits(repo, max_commits)` : Iterates oldest-to-newest
3. `extract_commit_info(commit, index, parent)` : Computes diff vs parent,
   reads source files that changed
4. `ingest_repository(url)` : Generator that yields `CommitInfo` objects

### `services/ast_parser.py`
Code entity extraction using Python's built-in `ast` module.

Key libraries:
- `ast` : Python's built-in Abstract Syntax Tree parser. Converts Python 
  source code into a tree of typed nodes (FunctionDef, ClassDef, Import, etc.)
- `re`  : Regex for JavaScript/TypeScript extraction

How Python parsing works:
1. `ast.parse(source)` → returns an AST node tree
2. `ast.walk(tree)` → yields every node in depth-first order
3. We check each node's type: `isinstance(node, ast.FunctionDef)` etc.
4. For call graphs, we use a NodeVisitor subclass that records `ast.Call` nodes

### `services/graph_builder.py`
Knowledge graph construction using NetworkX.

Key libraries:
- `networkx` : Graph algorithms library. We use `nx.DiGraph` (directed graph).
  Nodes = files/functions/classes. Edges = calls/imports/inherits.

How the "No Index" architecture works:
1. Build `G_before` (parent commit's graph) in memory
2. Build `G_after` (current commit's graph) in memory
3. Compute delta: `diff_graphs(G_before, G_after)` → added/removed/changed nodes
4. Serialise delta to JSON with `serialize_graph_diff()` → stored in SQLite
5. Discard both graphs (garbage collected) — saves memory vs storing every snapshot

### `services/metrics_engine.py`
Deterministic code health metric computation.

Key libraries:
- `radon` : Cyclomatic complexity calculator. `cc_visit(source)` returns 
  per-function complexity scores. Scale: 1-5 (simple) → 16+ (refactor urgently)

Metrics computed:
- **Complexity** : Mean cyclomatic complexity across all functions in changed files
- **Coupling** : Mean fan-out (outgoing edges) across function/class nodes in graph
- **Churn Risk** : composite score = normalised(churn_count) × normalised(coupling)
- **Spike detection** : if complexity grew > 25% vs parent → flag as spike

### `services/llm_service.py`
Cost-justified LLM integration. Three calls maximum per repo:

| Call | Trigger | Input | Output |
|------|---------|-------|--------|
| 1 — Spike Explainer | Complexity spike > 25% | Code diff + metrics | "Why did this happen? Intentional?" |
| 2 — Arch Summary | Post-ingestion (once) | JSON graph delta + stats | 3-sentence architectural summary |
| 3 — Demo Narrative | Post-ingestion (once) | Aggregated repo stats | Full health story walkthrough |

Key libraries:
- `openai` : Official OpenAI Python SDK. Uses `gpt-4o-mini` for cost efficiency.

### `background/ingestion_task.py`
Background thread worker that runs the full pipeline per repository.

How it works:
1. `start_ingestion(repo_id, url)` → launches a Python `threading.Thread`
2. FastAPI continues serving requests while the thread runs
3. Thread updates `Repository.status` and `Repository.processed_commits` every 10 commits
4. Frontend polls `/api/repos/{id}/status` every 3 seconds to show progress

---

## VS Code Step-by-Step Setup

### Prerequisites
- Python 3.11+ (`python --version`)
- Node.js 20+ (`node --version`)
- pnpm (`npm install -g pnpm`)

### 1. Clone and install

```bash
git clone <your-repo-url>
cd <project-directory>
pnpm install    # installs all JS/TS dependencies
```

### 2. Set up Python backend

```bash
cd python_backend
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate      # Linux/Mac
# OR
.venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 3. Set environment variables

```bash
# Required for LLM features (optional — app works without it)
export OPENAI_API_KEY=sk-...

# Backend port (default 8080)
export PORT=8080
```

Or create a `.env` file in `python_backend/`:
```
OPENAI_API_KEY=sk-...
PORT=8080
```

### 4. Start the Python API server

```bash
# From python_backend/ directory
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

API docs available at: http://localhost:8080/api/docs

### 5. Start the React frontend

In a new terminal:
```bash
# From project root
PORT=5173 BASE_PATH=/ pnpm --filter @workspace/repo-health run dev
```

Frontend at: http://localhost:5173

### 6. Ingest a test repository

With both servers running, open http://localhost:5173 and paste a GitHub URL, for example:
- `https://github.com/pallets/flask` (popular Python web framework, ~3000 commits)
- `https://github.com/expressjs/express` (Node.js, ~2000 commits)
- `https://github.com/fastapi/fastapi` (Python, ~1500 commits)

Set `maxCommits` to 100–200 for a quick demo. Full 500-commit analysis takes 5–10 minutes.

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/healthz | Health check |
| GET | /api/repos | List all repos |
| POST | /api/repos | Ingest new repo |
| GET | /api/repos/{id} | Get repo details |
| DELETE | /api/repos/{id} | Delete repo + data |
| GET | /api/repos/{id}/status | Poll ingestion progress |
| GET | /api/repos/{id}/stats | Aggregate stats |
| GET | /api/repos/{id}/commits | All commits with metrics |
| GET | /api/repos/{id}/commits/{sha} | Single commit detail |
| GET | /api/repos/{id}/timeline | Time-series for charts |
| GET | /api/repos/{id}/hotspots | File risk heatmap data |
| GET | /api/repos/{id}/riskiest-files | Top 10 risky files |
| GET | /api/repos/{id}/commits/{sha}/graph-diff | Knowledge graph diff |
| GET | /api/repos/{id}/commits/{sha}/spike-explanation | LLM spike analysis |
| GET | /api/repos/{id}/summary | Architectural summary |
| GET | /api/repos/{id}/narrative | Full health narrative |

Full interactive docs: http://localhost:8080/api/docs

---

## Troubleshooting

**Python packages not found:**
Make sure the virtual environment is activated (`source .venv/bin/activate`).

**Clone fails for private repos:**
Only public HTTPS URLs are supported. SSH URLs require SSH key setup.

**LLM calls return placeholder text:**
Set `OPENAI_API_KEY` environment variable. The app degrades gracefully without it.

**Large repo takes too long:**
Set `maxCommits` to 100–200 when ingesting. The analysis is proportional to commit count.

**Frontend shows "Replit Agent is building":**
The React frontend is being built by the design subagent. Wait a few minutes and refresh.
