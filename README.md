# SentinelAI

**AI-Powered Behavioral Anomaly Detection Platform**

Built for the Honeywell Hackathon.

> **Status: Phase 1 — Project Scaffolding.** No ML, synthetic data, detection, classification, explainability, or dashboard logic is implemented yet. This phase establishes the architecture, tooling, and wiring the rest of the platform will be built on.

## Tech Stack

| Layer | Stack |
|---|---|
| Frontend | React, TypeScript, Vite, TailwindCSS, React Router, Axios, TanStack Query, React Hook Form, Zod, Recharts, Lucide React |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, Pydantic v2, Uvicorn |
| AI | PyTorch, scikit-learn, NumPy, Pandas, SHAP |
| Infra | Docker, Docker Compose |

## Repository Structure
sentinel-ai/
├── frontend/ React + TypeScript SPA
├── backend/ FastAPI service
├── ai-engine/ Model development workspace (empty in Phase 1)
├── shared/ Cross-service contracts (empty in Phase 1)
├── docker/ Dockerfiles for backend and frontend
├── docs/ Architecture and design documentation
├── scripts/ Setup and developer tooling scripts
├── tests/ Cross-service integration/e2e tests (added in later phases)
└── .github/ CI workflows

<!-- See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the system design. -->

## Quick Start

1. Copy environment variables:
   ```bash
   cp .env.example .env
