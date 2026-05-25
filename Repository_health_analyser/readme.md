# RepoHealth

RepoHealth is a full-stack repository intelligence app for ingesting public Git repositories, analyzing commit-by-commit structural change, computing deterministic repo-health metrics, and visualizing how complexity, coupling, churn risk, and architectural drift evolve over time.

The app is built to answer the core engineering question:

> Which change merged, what structural shift did it cause, and how risky is that shift for the codebase?

## What is included

- FastAPI backend for ingestion orchestration, metrics, graph diffs, and insights APIs
- SQLite persistence for repositories, commits, file metrics, cached summaries, and narratives
- Git ingestion with `GitPython`
- AST and regex-backed source parsing for Python and JS/TS-family files
- `networkx` graph building and graph-diff serialization
- `radon` complexity scoring and risk metric aggregation
- optional OpenAI-powered spike explanations, architectural summaries, and repo narratives
- React + TypeScript frontend dashboard for timelines, hotspots, commit drill-downs, and insights
- OpenAPI-driven client generation with typed React Query hooks

## Project structure

```text
sacred_coder/
├─ python_backend/
│  ├─ background/
│  ├─ routers/
│  ├─ services/
│  ├─ database.py
│  ├─ main.py
│  ├─ models.py
│  ├─ README_VSCODE.md
│  └─ requirements.txt
├─ artifacts/
│  ├─ repo-health/
│  │  ├─ src/
│  │  ├─ public/
│  │  ├─ package.json
│  │  └─ vite.config.ts
│  └─ api-server/
├─ lib/
│  ├─ api-client-react/
│  ├─ api-spec/
│  ├─ api-zod/
│  └─ db/
├─ scripts/
├─ package.json
├─ pnpm-workspace.yaml
└─ README.md
```

## How the architecture maps to the project

### 1. Git ingestion

- implemented in `python_backend/services/git_ingestion.py`
- accepts public HTTPS repository URLs
- clones the target repository into a temporary directory
- walks commits chronologically and extracts changed files, line deltas, and file contents for supported source files

### 2. Code parsing

- implemented in `python_backend/services/ast_parser.py`
- parses Python via the built-in `ast` module
- extracts structural facts from JavaScript and TypeScript via regex-based analysis
- returns entities that are later used to construct dependency graphs and compute complexity summaries

### 3. Knowledge graph

- implemented in `python_backend/services/graph_builder.py`
- constructs graph nodes for files, classes, functions, and modules
- constructs edges for calls, imports, inheritance, and containment
- stores graph deltas per commit instead of persisting full graph snapshots

### 4. Deterministic metrics

- implemented in `python_backend/services/metrics_engine.py`
- complexity from `radon`
- coupling from graph fan-out and dependency relationships
- churn risk from file change frequency combined with coupling and complexity
- spike detection based on commit-over-commit complexity growth

### 5. Justified LLM usage

- implemented in `python_backend/services/llm_service.py`
- only used for:
  - complexity spike explanations
  - repository-level architectural summaries
  - one generated repo-health narrative
- if `OPENAI_API_KEY` is not set, the app falls back gracefully with placeholder explanations

### 6. Visualization

- implemented in `artifacts/repo-health/src/`
- includes:
  - repository ingestion dashboard
  - commit timeline views
  - hotspot risk table
  - graph diff visualization
  - architectural and narrative insight pages

## Step-by-step setup in VS Code

## 1. Open the project

Open the `sacred_coder` folder in VS Code.

## 2. Install Node workspace dependencies

In a VS Code terminal at the project root:

```powershell
cd "E:\HACKATHON 2026\Code-Sacred\sacred_coder"
pnpm install
```

## 3. Create the Python environment

In a second terminal:

```powershell
cd "E:\HACKATHON 2026\Code-Sacred\sacred_coder\python_backend"
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 4. Configure backend environment

Optional environment variables:

- `OPENAI_API_KEY` for LLM-powered summaries and spike explanations
- `PORT` if you want to run the backend on a port other than `8080`
- `REPO_HEALTH_DB` if you want the SQLite file stored in a different location

Example:

```powershell
$env:OPENAI_API_KEY="sk-..."
$env:PORT="8080"
```

## 5. Start the backend

From `python_backend/`:

```powershell
python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

The API will be available at:

- `http://127.0.0.1:8080/api/healthz`
- `http://127.0.0.1:8080/api/docs`

## 6. Start the frontend

From the project root in a new terminal:

```powershell
cd "E:\HACKATHON 2026\Code-Sacred\sacred_coder"
pnpm --filter @workspace/repo-health run dev
```

Open:

- `http://127.0.0.1:5173`

The Vite dev server is configured to proxy `/api/*` requests to `http://127.0.0.1:8080` during local development.

## 7. Run your first analysis

With both servers running, paste a public GitHub HTTPS URL into the dashboard, for example:

- `https://github.com/fastapi/fastapi`
- `https://github.com/pallets/flask`
- `https://github.com/expressjs/express`

The UI currently sends `maxCommits: 300` by default for ingestion.

## API endpoints

- `GET /api/healthz`
- `GET /api/repos`
- `POST /api/repos`
- `GET /api/repos/{repoId}`
- `DELETE /api/repos/{repoId}`
- `GET /api/repos/{repoId}/status`
- `GET /api/repos/{repoId}/stats`
- `GET /api/repos/{repoId}/commits`
- `GET /api/repos/{repoId}/commits/{sha}`
- `GET /api/repos/{repoId}/timeline`
- `GET /api/repos/{repoId}/hotspots`
- `GET /api/repos/{repoId}/riskiest-files`
- `GET /api/repos/{repoId}/commits/{sha}/graph-diff`
- `GET /api/repos/{repoId}/commits/{sha}/spike-explanation`
- `GET /api/repos/{repoId}/summary`
- `GET /api/repos/{repoId}/narrative`

## Important implementation notes

### Why SQLite instead of Postgres

This project keeps repo analysis self-contained inside `python_backend/repo_health.db`. That makes the app easy to demo, easy to move between machines, and independent from any shared database service.

### Why only graph deltas are stored

The project follows a lightweight storage model. Instead of saving a full graph snapshot for every commit, it computes the before/after delta and stores only the serialized diff. That keeps storage manageable while preserving the structural signal the UI needs.

### Why LLM usage is optional

The core value of the system comes from deterministic analysis first. Complexity, coupling, churn risk, commit metrics, and hotspot ranking all work without an API key. OpenAI is only used to enrich interpretation.

### Why background ingestion uses threads

Git walking, AST parsing, and metrics computation are blocking and CPU-heavy enough that a simple background thread is a practical fit here. FastAPI can keep serving requests while ingestion updates repository progress in SQLite.

## Troubleshooting

**`ERR_CONNECTION_REFUSED` on `http://localhost:5173/api/...`:**  
The frontend is running, but the FastAPI backend is not listening on port `8080`. Start the backend from `python_backend/` and verify `http://127.0.0.1:8080/api/healthz` works first.

**`ModuleNotFoundError: fastapi` or `uvicorn`:**  
Your virtual environment is not activated, or dependencies were installed into a different Python interpreter. Activate `.venv` and reinstall `requirements.txt`.

**`python --version` shows the wrong interpreter:**  
Use `py -3.12` explicitly when creating the venv. The app should be run from the environment where the backend packages are installed.

**GitHub repo ingestion fails immediately:**  
Make sure Git is installed and available in your terminal. `GitPython` relies on a working `git` executable for cloning.

**Private repositories do not ingest:**  
The current flow supports public HTTPS repositories only. SSH and authenticated private repo ingestion are not implemented in this UI.

**LLM insight endpoints return placeholder summaries:**  
Set `OPENAI_API_KEY`. Without it, the backend intentionally degrades gracefully and still serves deterministic metrics.

**The root `main.py` does not start the app you expect:**  
The real backend entrypoint is `python_backend/main.py`. The root-level `main.py` is not the FastAPI server.

## Suggested next improvements

- add authenticated private repository ingestion
- improve JS and TS parsing beyond regex extraction
- add branch and tag selection during ingestion
- add diff caching and clone reuse for repeat runs
- add exportable markdown or PDF reports for repository health snapshots

## Documentation map

- project summary: `replit.md`
- local backend and frontend setup: `python_backend/README_VSCODE.md`
- API contract source: `lib/api-spec/openapi.yaml`
- generated React Query client: `lib/api-client-react/src/generated/api.ts`
- generated Zod schemas: `lib/api-zod/src/generated/api.ts`
