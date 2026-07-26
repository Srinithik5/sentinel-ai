# SentinelAI — Deployment Guide

How to actually run this project, in every supported way, verified against the real Docker images and containers built and run during this project's development — not a hypothetical procedure.

## Table of Contents

- [Option A: Docker Compose (Recommended)](#option-a-docker-compose-recommended)
- [Option B: Minimal Manual Commands](#option-b-minimal-manual-commands)
- [Option C: Cross-Platform Setup Scripts](#option-c-cross-platform-setup-scripts)
- [Verifying the Stack Is Up](#verifying-the-stack-is-up)
- [Rebuilding After Code Changes](#rebuilding-after-code-changes)
- [Production Readiness — What's Real and What Isn't](#production-readiness--whats-real-and-what-isnt)
- [Running the AI Engine Pipeline](#running-the-ai-engine-pipeline)

---

## Option A: Docker Compose (Recommended)

```bash
cp .env.example .env
docker compose up -d --build
```

Three containers start: `sentinel-postgres`, `sentinel-backend`, `sentinel-frontend`. `docker-compose.yml` orders startup correctly — `backend` waits for Postgres's own healthcheck (`pg_isready`) before starting, and `frontend` waits for `backend`.

| Service | Container | URL |
|---|---|---|
| Frontend (SOC Dashboard) | `sentinel-frontend` | http://localhost:5173 |
| Backend (FastAPI) | `sentinel-backend` | http://localhost:8000 |
| API docs (Swagger) | `sentinel-backend` | http://localhost:8000/docs |
| Database | `sentinel-postgres` | `localhost:5432` (not exposed to the frontend/backend directly — see [Configuration.md](Configuration.md)) |

**No further setup steps.** Both Dockerfiles are `COPY`-based, self-contained builds — the backend installs `requirements.txt` and copies `app/`, `alembic/`; the frontend installs npm dependencies and copies the full source. Neither depends on anything already being installed on the host beyond Docker itself.

## Option B: Minimal Manual Commands

For running services outside Docker (e.g. active development with hot reload against a locally-installed Postgres):

```bash
# 1. Database — bring up just Postgres via Compose, or point at any local Postgres 16
docker compose up -d postgres

# 2. Backend
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt -r requirements-dev.txt   # .venv/bin/pip on macOS/Linux
.venv/Scripts/uvicorn app.main:app --reload --port 8000

# 3. Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

The frontend's `vite.config.ts` reads `PORT` from the environment (defaults to `5173`) and binds `host: true`, so it works identically whether started this way or via Docker.

## Option C: Cross-Platform Setup Scripts

`scripts/setup.sh` (macOS/Linux) and `scripts/setup.ps1` (Windows) both: copy `.env.example` to `.env` if missing, `npm install` the frontend, and create+populate a `.venv` for both `backend` and `ai-engine`. They do **not** start any service — run Option A or B afterward.

```bash
./scripts/setup.sh      # macOS/Linux
```
```powershell
.\scripts\setup.ps1      # Windows
```

## Verifying the Stack Is Up

```bash
curl http://localhost:8000/api/v1/health
```

Expected:
```json
{"status":"healthy","service":"sentinel-ai-backend","version":"1.0.0","database":"connected"}
```

Then open http://localhost:5173 — the Executive Overview should show real numbers (251,884 total events, 4,545 anomalies, etc.), not an empty/placeholder state. If it shows placeholder text like *"No alerts to display yet"*, the frontend Docker image is stale — see [Rebuilding After Code Changes](#rebuilding-after-code-changes) and [Troubleshooting.md](Troubleshooting.md).

## Rebuilding After Code Changes

**This is the single most important operational fact about this deployment**, discovered and documented after it caused real, confusing symptoms during development: both Dockerfiles use `COPY`, not a bind mount. Editing source on the host **does not** affect a already-running container. A code change requires an explicit rebuild:

```bash
docker compose build backend frontend
docker compose up -d backend frontend
```

`docker compose up -d` alone (without `--build`, and without the image having changed) reuses the existing image even if source files changed — the container's "Up X minutes" status in `docker ps` reflects when the *container* was last started, not when the *image* was last built. Check actual image build time with:

```bash
docker images sentinel-ai-frontend sentinel-ai-backend
```

## Production Readiness — What's Real and What Isn't

Honestly scoped, matching this project's documented limitations elsewhere:

| Aspect | Status |
|---|---|
| Non-root container user (backend) | ✅ Real — `docker/backend/Dockerfile` creates and switches to an `app` user |
| Structured request logging | ✅ Real — `structlog`-based, includes duration/status/client host per request |
| Healthcheck-gated startup ordering | ✅ Real — `docker-compose.yml`'s `depends_on: condition: service_healthy` |
| `ENVIRONMENT=production` code path | ✅ Real, but never exercised against an actual production deployment — see [Configuration.md](Configuration.md#development-vs-production-mode) |
| Frontend production build | ❌ Not implemented — the frontend Docker image runs `npm run dev` (Vite's development server), not a `vite build` + static-file server (e.g. nginx). Fine for a local demo; not how you'd ship this to real users. |
| TLS / HTTPS | ❌ Not implemented — everything is plain HTTP on localhost |
| Secrets management | ❌ Not implemented — `.env` with a plaintext password is the only mechanism |
| Cloud deployment | ❌ Not implemented — no Kubernetes manifests, no cloud provider config, no CDN |
| Database migrations | ⚠️ Scaffolded (`alembic/`) but empty — no models exist yet to migrate |

## Running the AI Engine Pipeline

The AI engine is not part of the Docker Compose stack — it's an offline CLI pipeline, run separately, whose output the frontend consumes as static files. See [ai-engine/README.md](../ai-engine/README.md) for the complete, phase-by-phase command reference. Quick version:

```bash
cd ai-engine
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
# Phases 2 -> 2B -> 2C -> 3 -> 4 -> 5 -> 6, then:
.venv/Scripts/python -m dashboard_export.dashboard_export_engine \
  --detection-results data/detections/<run_id>/detection_results.csv \
  --classification-results data/classifications/<run_id>/classification_report.csv \
  --explainability-dir data/explainability/<run_id> \
  --events data/features/<run_id>/engineered_events.parquet \
  --entities data/generated/<run_id>/entities.csv \
  --profile-store data/profiles/store \
  --output-dir ../frontend/public/data
```

After this, rebuild the frontend image (see above) so the running container picks up the fresh fixtures.
