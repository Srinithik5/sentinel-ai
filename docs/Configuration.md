# SentinelAI — Configuration Reference

Every environment variable this project actually reads, where it's consumed, and what happens if it's missing. One `.env` file at the repository root configures all three services (`backend`, `frontend`, and Docker Compose's `postgres` service) — there is no per-service `.env`.

## Table of Contents

- [Quick Setup](#quick-setup)
- [Environment Variables](#environment-variables)
- [Development vs. Production Mode](#development-vs-production-mode)
- [Docker Compose Variable Substitution](#docker-compose-variable-substitution)
- [The `localhost` vs. `postgres` Hostname Distinction](#the-localhost-vs-postgres-hostname-distinction)
- [`ai-engine/` Configuration](#ai-engine-configuration)

---

## Quick Setup

```bash
cp .env.example .env
```

`scripts/setup.sh` and `scripts/setup.ps1` do this automatically if `.env` doesn't already exist. The defaults in `.env.example` work as-is for local Docker Compose — only `POSTGRES_PASSWORD` should realistically be changed before any non-local use.

## Environment Variables

| Variable | Default (`.env.example`) | Consumed by | Purpose |
|---|---|---|---|
| `ENVIRONMENT` | `development` | `backend` (`Settings.ENVIRONMENT`) | One of `development`, `testing`, `production` — see [Development vs. Production Mode](#development-vs-production-mode) |
| `POSTGRES_USER` | `sentinel` | `docker-compose.yml` (postgres + backend `DATABASE_URL` substitution) | Database role name |
| `POSTGRES_PASSWORD` | `change_me` | same | Database role password — **change this before any shared or persistent use** |
| `POSTGRES_DB` | `sentinel_ai` | same | Database name |
| `POSTGRES_HOST` | `localhost` | Not read by any service directly today | Present for local (non-Docker) tooling; the backend's actual connection host is set via `DATABASE_URL` below |
| `POSTGRES_PORT` | `5432` | `docker-compose.yml` (postgres port mapping) | Host port Postgres is published on |
| `DATABASE_URL` | `postgresql+asyncpg://sentinel:change_me@localhost:5432/sentinel_ai` | `backend` (`Settings.DATABASE_URL`), **overridden** by `docker-compose.yml` for the containerized backend | Full async SQLAlchemy connection string — see [the localhost vs. postgres note](#the-localhost-vs-postgres-hostname-distinction) |
| `BACKEND_CORS_ORIGINS` | `http://localhost:5173` | `backend` (`Settings.cors_origins`) | Comma-separated list of origins allowed to call the API |
| `ALLOWED_HOSTS` | `*` | `backend` (`Settings.allowed_hosts`, `TrustedHostMiddleware`) | Comma-separated list of allowed `Host` headers |
| `LOG_LEVEL` | `INFO` | `backend` (`app/core/logging.py`) | structlog log level |
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | `frontend` (`services/api.ts`, build-time via Vite's `import.meta.env`) | Base URL the frontend's axios client targets |

Every backend variable is a field on the single `Settings` class (`backend/app/core/config.py`, `pydantic-settings`, `BaseSettings`) — there is no scattered `os.environ.get()` anywhere in the backend. Unset variables fall back to the typed defaults shown in that class, not to `.env.example`'s values (those are what ships in the example file, not a second layer of defaults).

`BACKEND_CORS_ORIGINS` and `ALLOWED_HOSTS` are deliberately typed as raw `str` fields on `Settings`, not `list[str]`, with `.cors_origins`/`.allowed_hosts` properties that split on `,` lazily. This is a documented, intentional choice (see the comment in `config.py`): `pydantic-settings` tries to JSON-decode any `list`-typed field sourced from an env var *before* custom validators run, so a plain comma-separated value like `http://localhost:5173` (not JSON) would crash `Settings()` at import time if the field were typed as `list[str]` directly.

## Development vs. Production Mode

Controlled entirely by `ENVIRONMENT`. `Settings.is_production` (a computed property) gates three things in `backend/app/main.py`:

```python
openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if not settings.is_production else None,
docs_url="/docs" if not settings.is_production else None,
redoc_url=None,  # custom route registered only if not settings.is_production — see main.py
```

| `ENVIRONMENT` | `/docs`, `/redoc`, `/api/v1/openapi.json` | Intended use |
|---|---|---|
| `development` (default) | Enabled | Local development, this hackathon submission |
| `testing` | Enabled (no special gating beyond `is_testing` being available for tests) | CI (`pytest`, see `.github/workflows/ci.yml`) |
| `production` | **Disabled** | Not exercised by anything in this repository today — no production deployment exists (see [Deployment.md](Deployment.md)) |

There is no separate `docker-compose.prod.yml` or production-specific Dockerfile in this repository — `ENVIRONMENT=production` is a real, working code path (verified by reading `main.py`'s conditionals directly), but it has not been exercised end-to-end against a real production deployment. Setting it locally will disable the docs routes; it will not, by itself, harden anything else (TLS, secrets management, and a production-grade frontend build are still separate, undone work — see Deployment.md).

## Docker Compose Variable Substitution

`docker-compose.yml` reads `.env` via `env_file: .env` for each service, **and** additionally substitutes `${POSTGRES_USER}`, `${POSTGRES_PASSWORD}`, `${POSTGRES_DB}` directly into the `postgres` service's `environment:` block and into a *computed* `DATABASE_URL` for the `backend` service:

```yaml
backend:
  environment:
    DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
```

This `environment:` value **overrides** whatever `DATABASE_URL` is set to in `.env` itself for the containerized backend — see the next section for why.

## The `localhost` vs. `postgres` Hostname Distinction

`.env.example`'s own `DATABASE_URL` uses `@localhost:5432` — correct for connecting to a Postgres instance running directly on your machine (e.g. running the backend outside Docker with `uvicorn app.main:app --reload`). Inside Docker Compose's network, `localhost` inside the `backend` container would refer to the container itself, not the `postgres` container — so `docker-compose.yml` explicitly recomputes `DATABASE_URL` using the Docker Compose service name `postgres` as the hostname instead. **You should never need to edit this yourself** — it's automatic — but it's worth understanding if `check_database_connection()` (and therefore `/api/v1/health`) ever reports `disconnected` unexpectedly: check which `DATABASE_URL` the backend process actually received (`docker compose exec backend env | grep DATABASE_URL`) before assuming Postgres itself is down.

## `ai-engine/` Configuration

The AI engine has **no environment variables at all** — every command takes its inputs and outputs as explicit CLI flags (see [ai-engine/README.md](../ai-engine/README.md)), so no `.env` file is read inside `ai-engine/`. This is deliberate: every phase is meant to be independently re-runnable against an arbitrary input path without touching global state. The root `.env` covers `backend`/`frontend` only.
