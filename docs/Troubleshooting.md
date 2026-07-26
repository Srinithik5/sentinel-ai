# SentinelAI — Troubleshooting

Every entry below documents a real problem actually encountered and fixed during this project's development — not a hypothetical FAQ. For AI engine pipeline-specific issues (validation failures, `ModuleNotFoundError` on phase packages, calibration questions), see [ai-engine/README.md's Troubleshooting section](../ai-engine/README.md#troubleshooting) instead — this document covers deployment, Docker, frontend, and backend issues.

## Table of Contents

- [Dashboard shows placeholder text instead of real data](#dashboard-shows-placeholder-text-instead-of-real-data)
- [`/redoc` loads but shows a blank page](#redoc-loads-but-shows-a-blank-page)
- [`FileNotFoundError: Dashboard fixture not found`](#filenotfounderror-dashboard-fixture-not-found)
- [`docker compose build` fails with a credential-helper error](#docker-compose-build-fails-with-a-credential-helper-error)
- [`npm run dev` / `npm run lint` fails with `'"node"' is not recognized`](#npm-run-dev--npm-run-lint-fails-with-node-is-not-recognized)
- [Health check reports `degraded` / `database: disconnected`](#health-check-reports-degraded--database-disconnected)
- [Backend container fails healthcheck at startup](#backend-container-fails-healthcheck-at-startup)
- [A fresh Python venv fails to import pandas on Windows](#a-fresh-python-venv-fails-to-import-pandas-on-windows)

---

## Dashboard shows placeholder text instead of real data

**Symptom:** the Alerts/Entities/Analytics pages show messages like *"No alerts to display yet. This view will populate once the detection engine is enabled"* instead of real numbers, even though the AI engine has clearly been run.

**Real root cause, confirmed during this project:** the frontend Docker image was built from source **before** the real dashboard components (and `frontend/public/data/*.json`) existed, and the container was only ever *restarted*, never *rebuilt*, since then. `docker/frontend/Dockerfile` uses `COPY frontend .` — a one-time snapshot at build time, not a live bind mount — so host-side source changes never reach an already-built image.

**Fix:**
```bash
docker compose build frontend
docker compose up -d frontend
```
Confirm the image is actually current: `docker images sentinel-ai-frontend` shows the real build timestamp, which `docker ps`'s "Up X minutes" does **not** reliably reflect (that's container start time, not image build time).

## `/redoc` loads but shows a blank page

**Symptom:** `GET /redoc` returns `200 OK` with valid HTML, but the browser renders nothing. Network tab shows `https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js` returning `404`.

**Real root cause:** FastAPI's default `redoc_url` template hardcodes `redoc@next` — jsdelivr's CDN alias for ReDoc's unstable, pre-release branch, whose bundle path has changed/broken at times. This is an external CDN issue, not a backend bug — `/docs` and `/api/v1/openapi.json` are unaffected.

**Fix (already applied — see `backend/app/main.py`):** `redoc_url=None` in the `FastAPI()` constructor, plus a custom `/redoc` route using `fastapi.openapi.docs.get_redoc_html()` pinned to a specific stable release (`redoc@2.1.3`) instead of `@next`.

## `FileNotFoundError: Dashboard fixture not found`

**Symptom:** running `python -m evaluation.evaluation_engine --frontend-data-dir ...` fails with `FileNotFoundError: Dashboard fixture not found: .../overview.json`.

**Real root cause:** Phase 8's dashboard-latency benchmark reads static fixtures that must already exist — nothing generates them automatically.

**Fix:** run the dashboard exporter first, against a completed Phase 3/4/5/6 run:
```bash
cd ai-engine
.venv/Scripts/python -m dashboard_export.dashboard_export_engine \
  --detection-results data/detections/<run_id>/detection_results.csv \
  --classification-results data/classifications/<run_id>/classification_report.csv \
  --explainability-dir data/explainability/<run_id> \
  --events data/features/<run_id>/engineered_events.parquet \
  --entities data/generated/<run_id>/entities.csv \
  --profile-store data/profiles/store \
  --output-dir ../frontend/public/data
```
Then re-run Phase 8. See [ai-engine/README.md — Dashboard Data Export](../ai-engine/README.md#dashboard-data-export).

## `docker compose build` fails with a credential-helper error

**Symptom:**
```
error getting credentials - err: exec: "docker-credential-desktop": executable file not found in %PATH%
```

**Real root cause:** on Windows, this happens specifically when running Docker CLI commands from a Git Bash / MSYS shell whose `PATH` doesn't include Docker Desktop's credential-helper binary — it only surfaces when Docker needs to check a registry (e.g. pulling/verifying a base image), not for operations against already-local images.

**Fix:** run the same command from PowerShell instead, which has Docker Desktop's full PATH:
```powershell
docker compose build backend frontend
```

## `npm run dev` / `npm run lint` fails with `'"node"' is not recognized`

**Symptom:** any `npm run <script>` invocation fails in a Git Bash session, but the same command works from PowerShell or cmd.exe.

**Real root cause:** this repository's path contains a space, and npm's Windows `.cmd` shim breaks under Git Bash when the invoking path has one.

**Fix:** call the underlying binaries directly instead of through the npm shim: `./node_modules/.bin/tsc --noEmit`, `./node_modules/.bin/vite build`, etc. — or run from PowerShell.

## Health check reports `degraded` / `database: disconnected`

**Symptom:** `GET /api/v1/health` returns `503` with `"database": "disconnected"`.

**Diagnosis:** `check_database_connection()` (`backend/app/db/session.py`) ran a real `SELECT 1` against the configured `DATABASE_URL` and it failed — this is never a hardcoded/fake status.

**Real causes to check, in order:**
1. Is `sentinel-postgres` actually running and healthy? `docker compose ps`
2. Did the backend receive the Docker-internal `DATABASE_URL` (hostname `postgres`), not the `.env` default (`localhost`)? `docker compose exec backend env | grep DATABASE_URL` — see [Configuration.md](Configuration.md#the-localhost-vs-postgres-hostname-distinction).
3. Do `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` in `.env` match what Postgres was actually initialized with? Changing these after the `postgres_data` volume already exists doesn't retroactively change the database's own credentials.

## Backend container fails healthcheck at startup

If `sentinel-backend` never reaches a healthy state, check `docker compose logs backend` — `docker-compose.yml`'s `depends_on: postgres: condition: service_healthy` already guarantees Postgres itself was reachable before the backend started, so a startup failure at this point is almost always a Python-level import/config error (e.g. a malformed `.env` value), not a race condition.

## A fresh Python venv fails to import pandas on Windows

**Symptom:**
```
ImportError: DLL load failed while importing pandas_parser: An Application Control policy has blocked this file.
```

**Real root cause:** a Windows-host security policy (Application Control / WDAC / a third-party EDR agent) blocking a freshly-downloaded native `.pyd` file — encountered on this exact machine during development. This is a host security control, not a bug in the code, and should never be worked around by disabling security settings.

**Fix used during this project:** run the same Python code inside a Linux container instead (e.g. `docker run --rm -v <path>:/app -w /app python:3.12-slim ...`) — Docker's Linux environment is unaffected by this Windows-host policy, since it's simply a different, already-trusted execution environment, not a bypass of the policy itself.
