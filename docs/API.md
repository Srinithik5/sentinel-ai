# SentinelAI — API Reference

The backend today exposes exactly **one** application endpoint. This document is deliberately short — it documents what is real and callable, not a planned surface. For why the dashboard doesn't call more endpoints than this, see [Frontend ↔ Backend Architecture](ARCHITECTURE.md#5-frontend--backend-architecture) in `ARCHITECTURE.md`.

## Table of Contents

- [Base URL](#base-url)
- [Interactive Documentation](#interactive-documentation)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [GET /api/v1/health](#get-apiv1health)
- [Error Format](#error-format)
- [Versioning](#versioning)
- [What's Not Here Yet](#whats-not-here-yet)

---

## Base URL

| Environment | Base URL |
|---|---|
| Local (Docker Compose) | `http://localhost:8000` |
| Frontend's configured base | `http://localhost:8000/api/v1` (`VITE_API_BASE_URL`, see [Configuration.md](Configuration.md)) |

All application routes are mounted under the `/api/v1` prefix (`app/core/config.py::API_V1_PREFIX`).

## Interactive Documentation

Auto-generated from the real FastAPI route/schema definitions — never hand-maintained, so it can't drift from the actual code:

| URL | What it is |
|---|---|
| `GET /docs` | Swagger UI |
| `GET /redoc` | ReDoc (pinned to `redoc@2.1.3` — see [Troubleshooting.md](Troubleshooting.md) for why) |
| `GET /api/v1/openapi.json` | The raw OpenAPI 3.1 schema |

All three are disabled automatically when `ENVIRONMENT=production` (`docs_url`/`openapi_url` become `None` in `app/main.py`).

## Authentication

**None.** No endpoint requires a credential today. The frontend's `apiClient` (`frontend/src/services/api.ts`) already has an `Authorization: Bearer <token>` interceptor wired in via `lib/authToken.ts`, but nothing ever calls `setAuthToken()` — it's forward-compatible scaffolding for when a real auth system is added, not an active mechanism.

## Endpoints

### `GET /api/v1/health`

Service and database connectivity check. Polled live by the frontend's `useHealthQuery` hook every 30 seconds — this is the **only** live request path between the frontend and backend today.

**Request:** no parameters, no body, no auth.

**Response — `200 OK`** (database reachable):

```json
{
  "status": "healthy",
  "service": "sentinel-ai-backend",
  "version": "1.0.0",
  "database": "connected"
}
```

**Response — `503 Service Unavailable`** (database unreachable):

```json
{
  "status": "degraded",
  "service": "sentinel-ai-backend",
  "version": "1.0.0",
  "database": "disconnected"
}
```

The endpoint deliberately returns a fully-formed, schema-valid body on `503`, not an empty error — `check_database_connection()` (`app/db/session.py`) runs a real `SELECT 1` against the configured database and the response reflects the actual result, never a hardcoded `"healthy"`. The frontend's `health.service.ts` explicitly treats both `200` and `503` as valid responses (`validateStatus`) so the dashboard can render a genuine degraded state instead of a generic network-error fallback.

| Field | Type | Values |
|---|---|---|
| `status` | string | `healthy`, `degraded` |
| `service` | string | `sentinel-ai-backend` (constant) |
| `version` | string | `1.0.0` (constant, from `Settings.VERSION`) |
| `database` | string | `connected`, `disconnected` |

## Error Format

Unhandled exceptions and validation errors are normalized by `app/core/exceptions.py::register_exception_handlers` into a consistent JSON shape (FastAPI's standard `{"detail": ...}` pattern for validation errors; a structured error body for registered exception handlers). Since only one endpoint exists and it has no request parameters to validate, this mostly matters for future endpoints — documented here so the contract is established before more routes are added.

## Versioning

The `/api/v1` prefix is the only version in use. `API_V1_PREFIX` is a single `Settings` field (`app/core/config.py`), so introducing `/api/v2` later means adding a new prefixed router, not restructuring the existing one.

## What's Not Here Yet

No endpoints exist for alerts, entities, analytics, detection results, or classifications. The SOC dashboard (Phase 7) reads that data from static JSON fixtures in `frontend/public/data/`, written by the ai-engine's `dashboard_export` stage — see [ai-engine/README.md](../ai-engine/README.md#dashboard-data-export). Building real backend-served domain endpoints for this data is documented future work (see `ARCHITECTURE.md`'s Current Limitations), not an oversight — this document will grow when that work happens, not before.
