# SentinelAI — Folder Structure

A complete map of the repository: what every top-level and second-level directory is for, and — critically — which ones are intentionally empty placeholders versus which ones hold real, working code. Distinguishing the two matters for a hackathon submission: nothing below is dead weight left by accident, but not everything is implemented yet either.

## Table of Contents

- [Top-Level Layout](#top-level-layout)
- [`frontend/`](#frontend)
- [`backend/`](#backend)
- [`ai-engine/`](#ai-engine)
- [`docker/`](#docker)
- [`docs/`](#docs)
- [Intentionally Empty Directories](#intentionally-empty-directories)
- [Generated / Gitignored Directories](#generated--gitignored-directories)

---

## Top-Level Layout

```
sentinel-ai/
├── frontend/           React 18 + TypeScript + Vite SOC dashboard (Phase 7)
├── backend/             FastAPI service (health check only today)
├── ai-engine/             Python AI pipeline — Phases 2 through 8, dashboard_export
├── docker/                 Dockerfiles for backend and frontend
├── docs/                     Architecture, API, deployment, and configuration docs
├── scripts/                   Cross-platform setup scripts (setup.sh, setup.ps1)
├── shared/                     Reserved for future cross-service contracts (empty)
├── tests/                       Reserved for future root-level integration tests (empty)
├── .github/workflows/            CI pipeline (frontend build, backend pytest)
├── docker-compose.yml
├── .env.example
└── README.md
```

Every service (`frontend/`, `backend/`, `ai-engine/`) is independently runnable and independently documented — this file is the map; [README.md](../README.md), [ai-engine/README.md](../ai-engine/README.md), and this `docs/` folder are the detail.

## `frontend/`

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/              Radix-based primitives (Button, Table, Sheet, Tabs, Select, ...)
│   │   ├── dashboard/        SOC dashboard domain components (AlertQueue, MitrePanel, ...)
│   │   ├── analytics/         Chart components (Recharts-based)
│   │   ├── system/             System Health panel components
│   │   └── layout/              Sidebar, Topbar, page shell
│   ├── pages/                 One file per route (DashboardPage, AlertsPage, ...)
│   ├── hooks/                   TanStack Query hooks (useDashboardData, useHealthQuery, ...)
│   ├── services/                  axios client + typed fetch functions (api.ts, dashboard.service.ts, health.service.ts)
│   ├── types/                      TypeScript contracts (dashboard.ts — the frontend/ai-engine data contract)
│   ├── routes/                      Route path constants and router config
│   └── lib/                          Formatting helpers, auth-token placeholder
├── public/data/                        JSON fixtures written by ai-engine's dashboard_export (not gitignored — real deploy artifacts)
├── vite.config.ts
├── tailwind.config.ts
└── package.json
```

**Two files worth knowing about explicitly**, both confirmed genuinely unused during this audit and left in place rather than silently deleted without disclosure — see [SUBMISSION_CHECKLIST.md](../SUBMISSION_CHECKLIST.md) for the removal recommendation:

- `components/system/BackendStatusCard.tsx` — an earlier, simpler health-status card superseded by `components/system/SystemHealthPanel.tsx` in Phase 7. Never imported anywhere.
- `components/ui/Progress.tsx` — a Radix progress-bar primitive scaffolded alongside Phase 7's other UI primitives but never wired into a consuming component.

`lib/authToken.ts` (`getAuthToken`/`setAuthToken`) is intentional forward-compatible scaffolding, not dead code — `setAuthToken` is never called today (`getAuthToken()` always returns `null`), but the axios interceptor in `services/api.ts` already reads it, so adding real authentication later won't require touching the request layer.

## `backend/`

```
backend/
├── app/
│   ├── api/v1/endpoints/health.py    The only implemented route: GET /api/v1/health
│   ├── core/                          Settings, logging, middleware registration, exception handlers
│   ├── middleware/                     TimingMiddleware, RequestLoggingMiddleware (structlog-based)
│   ├── db/                              Async SQLAlchemy engine/session + connectivity check
│   ├── models/                           Empty — reserved for future ORM models
│   ├── repositories/                      Empty — reserved for future data-access layer
│   ├── services/                           Empty — reserved for future business logic
│   ├── schemas/                             Pydantic response schemas (health.py)
│   └── main.py                                FastAPI app factory
├── alembic/                                    Migration scaffolding (no migrations written yet — no models exist)
├── tests/test_health.py                          The one existing test, verified passing
├── requirements.txt / requirements-dev.txt
```

`app/models/`, `app/repositories/`, and `app/services/` are genuinely empty (only an `__init__.py` each) — this is not an oversight, it mirrors the documented, disclosed reality that this backend has no domain endpoints yet. They exist so the intended layered structure (route → service → repository → model) is visible even before it's populated.

## `ai-engine/`

See [ai-engine/README.md](../ai-engine/README.md) for the complete, authoritative breakdown — summarized here for cross-reference:

```
ai-engine/
├── generators/, attacks/, features/       Phases 2, 2B, 2C — synthetic data, attack injection, feature engineering
├── profiles/                               Phase 3 — behaviour baseline learning and storage
├── detection/                                Phase 4 — anomaly detection and risk scoring
├── classification/                            Phase 5 — attack classification and MITRE mapping
├── explainability/                             Phase 6 — analyst-facing explanations
├── dashboard_export/                            Bridges real pipeline output into frontend/public/data/*.json
├── evaluation/                                    Phase 8 — independent metrics, benchmarks, reports
├── outputs/, validators/                            Shared writer/validator primitives, one module per phase
├── config/, schemas/, utils/, ground_truth/          Shared config, data contracts, and helpers
├── models/, notebooks/                                Empty — reserved for future trained-model artifacts and analysis
└── data/                                                Every phase's generated output (gitignored except .gitkeep)
```

## `docker/`

```
docker/
├── backend/Dockerfile      python:3.12-slim, non-root user, COPY-based (not a bind mount)
└── frontend/Dockerfile      node:20-alpine, runs the Vite dev server (see Deployment.md for what this means for production)
```

## `docs/`

```
docs/
├── ARCHITECTURE.md        System-wide architecture, 8 Mermaid diagrams, data contracts
├── API.md                   Every real backend endpoint (currently: one)
├── Deployment.md              Docker Compose, dev vs. production mode, what's missing for real production
├── Configuration.md             Every environment variable, defaults, and where each is consumed
├── Troubleshooting.md             Real, previously-encountered problems and their actual fixes
├── FolderStructure.md               This file
└── DEMO.md                            Real datasets, a real screenshot checklist, real analyst/attack scenarios
```

## Intentionally Empty Directories

These are not bugs — each one carries its own `README.md` (or, for `ai-engine/models`/`ai-engine/notebooks`, is documented in `ai-engine/README.md`) explicitly stating why it's empty and what it's reserved for:

| Directory | Reserved for |
|---|---|
| `shared/` | Cross-service TypeScript/Pydantic contracts, once the backend has real domain endpoints for the frontend to type against |
| `tests/` | Root-level end-to-end tests spanning frontend + backend + ai-engine, once real integration flows exist |
| `backend/app/models/`, `repositories/`, `services/` | The backend's domain layer, once real endpoints are built |
| `ai-engine/models/` | Trained ML model artifacts, once a model is actually trained (see Current Limitations in ARCHITECTURE.md) |
| `ai-engine/notebooks/` | Exploratory data analysis notebooks |

## Generated / Gitignored Directories

| Directory | Contents | Tracked? |
|---|---|---|
| `ai-engine/data/*` | Every phase's timestamped run output | No (`.gitkeep` only) |
| `ai-engine/models/*` | Future trained model artifacts | No (`.gitkeep` only) |
| `frontend/public/data/*.json` | Dashboard fixtures written by `dashboard_export` | **Yes** — these are real deploy artifacts the frontend serves, not build output |
| `frontend/dist/`, `node_modules/`, `.venv/`, `__pycache__/` | Build/dependency artifacts | No |
