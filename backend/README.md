# SentinelAI Backend

FastAPI service for SentinelAI — Phase 1B: production-grade backend infrastructure. No business logic, authentication, or ML is implemented yet; this is the foundation those phases build on.

## Architecture

The backend follows Clean Architecture: each layer has a single responsibility and depends only on the layers beneath it.

\`\`\`
Request
  │
  ▼
middleware/           (cross-cutting: timing, structured request logging)
  │
  ▼
core/middleware.py     (composition root — registers built-in + custom middleware)
  │
  ▼
api/v1/endpoints/       (HTTP boundary — routing, request/response schemas)
  │
  ▼
services/               (business logic — empty until Phase 2+)
  │
  ▼
repositories/           (data access — empty until Phase 2+)
  │
  ▼
db/session.py           (async SQLAlchemy engine/session)
  │
  ▼
PostgreSQL
\`\`\`

Cross-cutting concerns (`core/config.py`, `core/logging.py`, `core/exceptions.py`) are available to every layer without creating circular dependencies, since nothing below `core/` imports from `api/`, `services/`, or `repositories/`.

### Folder Purpose

| Folder | Purpose |
|---|---|
| `api/v1/endpoints/` | Route handlers, one module per resource |
| `api/v1/router.py` | Aggregates endpoint routers into a single versioned router |
| `api/dependencies.py` | Shared FastAPI dependency type aliases (`DBSession`, `SettingsDep`) |
| `core/config.py` | Typed, environment-based settings (development/testing/production) |
| `core/logging.py` | Structured logging configuration (structlog + stdlib) |
| `core/exceptions.py` | Global exception handlers — validation, database, unhandled |
| `core/middleware.py` | Registers all middleware on the app in the correct order |
| `db/base.py` | SQLAlchemy declarative base with a fixed constraint-naming convention |
| `db/session.py` | Async engine, session factory, `get_db` dependency, health check |
| `models/` | SQLAlchemy ORM models (empty — Phase 2+) |
| `schemas/` | Pydantic request/response contracts |
| `repositories/` | Data-access layer (empty — Phase 2+) |
| `services/` | Business logic (empty — Phase 2+) |
| `middleware/` | Custom ASGI middleware implementations (timing, request logging) |
| `startup/` | Application lifespan hooks (startup/shutdown) |
| `utils/` | Shared helpers (empty) |
| `main.py` | Application factory — assembles the FastAPI instance |

## Running

### Docker (recommended)

From the repository root:

\`\`\`bash
docker compose up --build backend postgres
\`\`\`

### Local

\`\`\`bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/uvicorn app.main:app --reload
\`\`\`

Requires a reachable PostgreSQL instance matching `DATABASE_URL`.

### Tests

\`\`\`bash
cd backend
.venv/Scripts/pytest
\`\`\`

### Migrations

\`\`\`bash
cd backend
.venv/Scripts/alembic revision --autogenerate -m "message"
.venv/Scripts/alembic upgrade head
\`\`\`

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | `development`, `testing`, or `production` — controls docs exposure and log rendering |
| `API_V1_PREFIX` | `/api/v1` | Prefix under which all versioned routes are mounted |
| `DATABASE_URL` | `postgresql+asyncpg://sentinel:change_me@localhost:5432/sentinel_ai` | Async SQLAlchemy connection string |
| `DATABASE_POOL_SIZE` | `5` | SQLAlchemy connection pool size |
| `DATABASE_MAX_OVERFLOW` | `10` | Additional connections allowed beyond pool size |
| `DATABASE_ECHO` | `false` | Log all SQL statements (debugging only) |
| `BACKEND_CORS_ORIGINS` | `http://localhost:5173` | Comma-separated list of allowed CORS origins |
| `ALLOWED_HOSTS` | `*` | Comma-separated list of allowed `Host` headers — restrict in production |
| `LOG_LEVEL` | `INFO` | Root logger level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## Health Endpoint

\`\`\`
GET /api/v1/health
\`\`\`

Returns `200` when the database is reachable, `503` otherwise:

\`\`\`json
{
  "status": "healthy",
  "service": "sentinel-ai-backend",
  "version": "1.0.0",
  "database": "connected"
}
\`\`\`

## Logging

All logs are structured (via `structlog`) and include timestamp, level, logger name, and message, plus contextual fields (e.g. `method`, `path`, `status_code`, `duration_ms` for request logs). Console-rendered in development, JSON-rendered in production.

## Exception Handling

Four global handlers, registered in `core/exceptions.py`:

- `RequestValidationError` → `422` with field-level error detail
- `AppException` (and subclasses) → the exception's own status code
- `SQLAlchemyError` → `503`, with the underlying error logged but not exposed
- Any other unhandled `Exception` → `500`, with a generic message and a logged stack trace