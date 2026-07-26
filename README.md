![Status](https://img.shields.io/badge/status-Phase%208%20Complete-brightgreen) ![Python](https://img.shields.io/badge/python-3.12-blue) ![Node](https://img.shields.io/badge/node-18%2B-339933) ![Determinism](https://img.shields.io/badge/pipeline-deterministic-informational)

# SentinelAI

**AI-Powered Behavioral Anomaly Detection and Threat Intelligence Platform**

Built for the Honeywell Hackathon.

> **Status: Phase 8 complete.** Synthetic enterprise simulation, behavioural profiling, anomaly detection, risk scoring, threat classification, analyst-facing explainability, an Enterprise SOC Dashboard, and an independent evaluation framework are implemented and verified end-to-end against real generated data (251,884 events / 2,500 entities; 4,545 flagged events classified and explained). A live backend-served domain API, a trained ML model, and real-time streaming ingestion are the next planned phases and are **not** implemented yet.

---

## Table of Contents

- [Architecture](#architecture)
  - [Complete AI Security Pipeline](#complete-ai-security-pipeline)
  - [System Architecture](#system-architecture)
  - [Data Flow](#data-flow)
  - [Detection → Classification Flow](#detection--classification-flow)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Completed Phases](#completed-phases)
- [Design Principles](#design-principles)
- [Quick Start](#quick-start)
- [Roadmap](#roadmap)
- [Design Tokens](#design-tokens)

---

## Architecture

### Complete AI Security Pipeline

```mermaid
flowchart TD
    A["Synthetic Enterprise Data<br/>Phase 2"] --> B["Attack Injection & Ground Truth<br/>Phase 2B"]
    B --> C["Feature Engineering<br/>Phase 2C"]
    C --> D["Behaviour Profiling<br/>Phase 3"]
    D --> E["Anomaly Detection<br/>Phase 4"]
    E --> F["Risk Scoring<br/>Phase 4"]
    F --> G["Threat Classification<br/>Phase 5"]
    G --> H["MITRE ATT&CK Intelligence<br/>Phase 5"]
    H --> I["Explainability Engine<br/>Phase 6"]
    I --> J["Dashboard Data Export"]
    J --> K["Enterprise SOC Dashboard<br/>Phase 7"]
    D -.-> L["Enterprise Evaluation Framework<br/>Phase 8"]
    F -.-> L
    G -.-> L
    J -.-> L
```

Each stage is a separate, independently runnable module in [`ai-engine/`](ai-engine/) that consumes the previous stage's file-based output (CSV / Parquet / JSON) and never modifies it — see [Completed Phases](#completed-phases) for what each stage actually does. Phase 8 (dashed lines) is not a sequential pipeline stage — it's a separate, read-only evaluation layer over Phases 3–5 and the dashboard fixtures.

### System Architecture

```mermaid
flowchart LR
    subgraph Client["Client"]
        FE["React + TypeScript Frontend\n(Vite, TailwindCSS, TanStack Query)"]
    end

    subgraph Server["Backend Service"]
        BE["FastAPI Backend\n(async SQLAlchemy 2, structlog)"]
        DB[("PostgreSQL")]
    end

    subgraph Engine["AI Engine — Offline Pipeline (CLI)"]
        GEN["Generators\nPhase 2"]
        ATK["Attack Injection\nPhase 2B"]
        FEAT["Feature Engineering\nPhase 2C"]
        PROF["Behaviour Profiling\nPhase 3"]
        DET["Detection Engine\nPhase 4"]
        CLS["Classification Engine\nPhase 5"]
        EXP["Explainability Engine\nPhase 6"]
        DASH["Dashboard Data Export"]
        GEN --> ATK --> FEAT --> PROF --> DET --> CLS --> EXP --> DASH
    end

    FE -- "health check only" --> BE
    BE <--> DB
    DASH -- "static JSON fixtures\nfrontend/public/data/" --> FE
```

**Current integration boundary:** the frontend and backend form a working, connected web application, but the only *live* request path between them is the health check. The AI Engine's real pipeline output reaches the frontend through the Dashboard Data Export stage, which writes static JSON fixtures the frontend reads directly at page load — not through the backend. A live backend-served domain API for this data (alerts, entities, analytics) does not exist yet — that's still future work (see [Roadmap](#roadmap)).

### Data Flow

```mermaid
flowchart LR
    E1["entities.csv / events.csv\nPhase 2"] --> E2["events_injected.csv\nground_truth.csv\nPhase 2B"]
    E2 --> E3["engineered_events.parquet\nPhase 2C"]
    E3 --> E4["profile store (JSON)\nPhase 3"]
    E3 --> E5["detection_results.csv/.parquet\nPhase 4"]
    E4 --> E5
    E5 --> E6["classification_report.csv/.parquet\nPhase 5"]
    E4 --> E6
```

Every arrow is a file on disk, not an in-memory handoff — each phase can be re-run independently against any prior phase's saved output, which is what makes every stage separately testable and auditable.

### Detection → Classification Flow

```mermaid
flowchart TD
    EV["Incoming Event\n(engineered feature row)"] --> PC["Profile Comparator\n6 behavioural dimensions"]
    PC --> AS["Anomaly Scorer\n(weighted_average / max_deviation)"]
    AS --> RE["Risk Engine\n0-100 normalized risk score"]
    RE --> TM["Threshold Manager\n5 severity levels"]
    TM --> DE["Decision Engine"]
    DE -->|Normal| N["No further action"]
    DE -->|Suspicious or Anomalous| EC["Evidence Collector"]
    EC --> AC["Attack Classifier\n(rule-based strategy)"]
    AC --> CE["Confidence Engine\n0.0-1.0 confidence"]
    CE --> MM["MITRE Mapper"]
    MM --> RESULT["Classification Result:\nAttack Type, Confidence, Severity,\nMITRE Tactic, MITRE Technique, Evidence"]
```

Ground truth labels are **never** read by any component in this diagram — they are attached to results only after both `DetectionEngine.detect()` and `ClassificationEngine.classify()` return, purely to compute retrospective evaluation metrics.

---

## Tech Stack

| Layer | Stack |
|---|---|
| **Frontend** | React, TypeScript, Vite, TailwindCSS, React Router, Axios, TanStack Query, React Hook Form, Zod, Recharts, Lucide React |
| **Backend** | Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Pydantic, Uvicorn |
| **AI** | PyTorch, scikit-learn, NumPy, Pandas, SHAP |
| **Infrastructure** | Docker, Docker Compose |

> The AI Engine's implemented pipeline (Phases 2–8) is currently built on **Pandas, NumPy, PyArrow, and Faker** using deterministic statistical and rule-based methods — no model has been trained yet. Phase 6's explainability engine is likewise fully rule-based and deterministic; it does not use SHAP. PyTorch, scikit-learn, and SHAP remain scaffolded, unused dependencies (confirmed via a full source audit) reserved for a future trained-model phase on the [Roadmap](#roadmap).

## Repository Structure

```
sentinel-ai/
├── frontend/               React + TypeScript SPA
├── backend/                FastAPI service
├── ai-engine/               Behavioural anomaly detection, classification & evaluation pipeline
│   ├── generators/          Synthetic enterprise entity & event generation (Phase 2)
│   ├── profiles/            Behaviour baseline learning & profile store (Phase 3)
│   ├── features/            Behavioural feature engineering pipeline (Phase 2C)
│   ├── detection/           Anomaly detection & risk scoring engine (Phase 4)
│   ├── classification/      Attack classification & MITRE mapping engine (Phase 5)
│   ├── explainability/      Analyst-facing explanations & recommendations (Phase 6)
│   ├── dashboard_export/    Bridges pipeline output into frontend/public/data fixtures
│   ├── evaluation/          Independent metrics, benchmarks & reports (Phase 8)
│   ├── outputs/             Report / CSV / Parquet / JSON writers for every phase
│   └── validators/          Validation suites for every phase
├── shared/                 Cross-service contracts
├── docker/                 Dockerfiles for backend and frontend
├── docs/                   Architecture and design documentation
├── scripts/                Setup and developer tooling scripts
└── tests/                  Cross-service integration/e2e tests
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the system design and [ai-engine/README.md](ai-engine/README.md) for the full module-by-module breakdown of every AI pipeline phase (including the `attacks/`, `config/`, `ground_truth/`, and `schemas/` supporting modules, omitted above for brevity).

**Full documentation set:** [Architecture](docs/ARCHITECTURE.md) · [API Reference](docs/API.md) · [Deployment](docs/Deployment.md) · [Configuration](docs/Configuration.md) · [Troubleshooting](docs/Troubleshooting.md) · [Folder Structure](docs/FolderStructure.md) · [Demo Guide](docs/DEMO.md) · [Submission Checklist](SUBMISSION_CHECKLIST.md)

---

## Completed Phases

### Phase 1 — Project Scaffolding

- Monorepo architecture
- Frontend / backend / AI-engine structural separation
- Development environment setup
- Docker foundation (Dockerfiles + Compose)
- Base tooling and CI scaffolding

### Phase 2 — Synthetic Enterprise Environment Generator

- Enterprise-scale synthetic event generation
- User / entity behaviour simulation
- CSV generation
- Parquet generation
- Behaviour profiles
- Dataset dictionary
- Generation reports

Generated realistic enterprise activity data used as the input for every downstream phase.

### Phase 3 — Behaviour Profiling Engine

- Behaviour baseline generation
- Entity profile store
- Entity modelling
- Multi-dimensional behavioural analysis
- Historical behavioural profiles
- Profile versioning support

Profiles capture six behavioural dimensions:

- Temporal
- Device
- Resource
- Geographic
- Authentication
- Session

### Phase 4 — Anomaly Detection and Risk Scoring Pipeline

Completed and verified.

**DetectionEngine**
- End-to-end detection workflow orchestration

**Profile Comparator**
- Six-dimensional behavioural comparison (Temporal, Device, Resource, Geographic, Authentication, Session)

**Anomaly Scorer**
- Pluggable scoring strategies:
  - `weighted_average`
  - `max_deviation`

**Risk Engine**
- Combines five risk factors
- Produces a normalized 0–100 risk score

**Threshold Manager**
- Five configurable severity levels
- Strictly increasing boundaries

**Decision Engine**
- Maps risk scores into:
  - Normal
  - Suspicious
  - Anomalous

**Streaming architecture**
- `StreamProcessor.process_event` is the single, sequential execution path used for both historical replay and live-style event-at-a-time processing

**Validation**
- 251,884 events
- 2,500 entities
- Deterministic execution
- Zero validation errors

**Outputs**
- Detection Results (CSV)
- Detection Results (Parquet)
- Risk Score Report
- Detection Metrics
- Detection Summary
- Validation Report

### Phase 5 — Threat Classification and MITRE Intelligence

Completed and verified.

**ClassificationEngine**
- Coordinates the complete attack classification workflow

**Evidence Collector**
- Gathers evidence from:
  - Detection scores
  - Engineered features
  - Behaviour profiles
  - MITRE metadata
  - Historical profile activity

**Strategy Pattern**
- Current: rule-based classifier
- Future: pluggable ML classifier integration, without changing the engine

**Confidence Engine**
- Produces a 0.0–1.0 confidence score per classification

**Attack Registry**
- Maintains name, description, indicators, severity, and MITRE ATT&CK mapping per attack type

**Supported classifications**

- `brute_force`
- `impossible_travel`
- `credential_stuffing`
- `lateral_movement`
- `device_spoofing`
- `low_and_slow_exfiltration`
- `insider_drift`
- `unknown`

**MITRE ATT&CK mapping**

Every classification contains:

- Attack Type
- Confidence
- Severity
- MITRE Tactic
- MITRE Technique
- Evidence

**Verification**

- 4,545 flagged events classified (final verified run, from the 251,884-event / 2,500-entity Phase 4 dataset)
- Validation PASSED
- 0 errors
- 0 warnings

**Outputs**
- Classification Report (CSV)
- Classification Report (Parquet)
- Attack Summary
- Confidence Distribution
- Validation Report

### Phase 6 — Explainability Engine

Completed and verified.

For every event Phase 5 already classified, transforms the detection and classification output into an analyst-facing explanation — no re-scoring, no re-classification, purely aggregation and narrative generation over values earlier phases already computed.

- **Evidence Aggregator** — merges Phase 4 detection scores, Phase 5 classification output, Phase 2C engineered features, and the entity's Phase 3 profile into one evidence bundle
- **Feature Attribution Engine** — normalizes Phase 4's six deviation dimensions into contribution percentages that sum to 100
- **Reason Generator** — a four-part narrative: behaviour deviation, historical comparison, feature impact, attack indicators
- **Confidence Explainer** — decomposes Phase 5's confidence score into match strength, margin, and detection strength
- **Recommendation Engine** — attack-type-specific analyst actions plus automatic High/Critical severity escalation
- **Analyst Summary** — one structured record per event: entity, risk score, attack type, confidence, severity, MITRE mapping, top indicators, evidence summary, recommended actions

**Verification:** 4,545 events explained, from the same Phase 5 run referenced above. Validation PASSED — 0 errors, 0 warnings.

### Phase 7 — Enterprise SOC Dashboard

Completed and verified.

A React/TypeScript SOC dashboard covering Executive Overview, Live Alert Queue, Alert Details Panel, Explainability Panel, Behaviour Timeline, MITRE ATT&CK Panel, Analytics, and System Health. It consumes real Phase 3–6 output through the Dashboard Data Export stage below — static JSON fixtures in `frontend/public/data/` — not a live backend API (see the corrected [System Architecture](#system-architecture) diagram above).

**Verification:** `tsc -b` and `vite build` both run clean; the dashboard was exercised through live browser testing (search/filter/sort/pagination, every detail-panel tab, all analytics charts, responsive breakpoints). Three real bugs were found and fixed during that testing — see [ai-engine/README.md](ai-engine/README.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the specifics.

**Dashboard Data Export** — the stage that produces `frontend/public/data/*.json` for Phase 7 (and for Phase 8's dashboard-latency benchmark, below) has itself been run against real data: validation PASSED with 0 errors and 0 warnings, and its output was diffed field-by-field against a prior fixture set with zero differences outside one deliberately-live timing measurement (documented as such in the fixture itself). See [ai-engine/README.md's Dashboard Data Export section](ai-engine/README.md#dashboard-data-export) for the full verification record — this is a real, run-once verification of that specific stage, not a claim that every possible input combination has been exercised.

### Phase 8 — Enterprise Evaluation Framework

Completed and verified.

An independent, read-only benchmarking layer, not part of the sequential pipeline: it recomputes Detection and Classification metrics from scratch against ground truth — deliberately never reading Phases 4/5's own reported numbers — and separately evaluates cold-start behaviour, concept drift, scalability (up to 50,000 entities), streaming throughput, and dashboard data latency.

**Verification:** the independently-recomputed Detection metrics (precision 0.2840, recall 0.7882, F1 0.4176, ROC-AUC 0.9932) exactly reproduced Phase 4's own separately-computed figures — a genuine cross-validation of both implementations, not an assumption that one is correct. A full run against real data completed with Validation PASSED — 0 errors, 0 warnings.

---

## Design Principles

- **Detection and classification are separate stages** — Phase 4 only ever answers "is this anomalous?"; Phase 5 only ever answers "which attack type does this resemble?"
- **Ground truth isolation** — labels are never read as an inference input anywhere in the pipeline; they are attached to results only after detection/classification completes, for evaluation only
- **Explainability** — every classification carries the concrete evidence (matched indicators) that produced it, not just a bare label
- **Deterministic pipelines** — no randomness in scoring, detection, or classification logic; identical input always produces identical output
- **Reproducible experiments** — every run is versioned, timestamped, and written to its own output directory alongside a validation report
- **Strategy-based extensibility** — anomaly scoring and attack classification are both built behind swappable strategy interfaces, so a future trained model can be substituted without touching the surrounding engine
- **Streaming readiness** — the core processing unit (`StreamProcessor.process_event`) handles exactly one event at a time; batch replay is a thin loop around the same path a live feed would use

---

## Quick Start

### 1. Environment Setup

```bash
cp .env.example .env
```

### 2. Run the Web Stack (Docker)

```bash
docker compose up --build
```

Open:
- Frontend: http://localhost:5173
- Backend health check: http://localhost:8000/api/v1/health
- API docs: http://localhost:8000/docs

For local (non-Docker) setup, see the setup scripts in [scripts/](scripts/).

### 3. Run the AI Pipeline

```bash
cd ai-engine
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt

# Phase 2 — generate the synthetic enterprise dataset
.venv/Scripts/python generate_dataset.py

# Phase 2B — inject attacks + ground truth
.venv/Scripts/python attack_orchestrator.py --dataset-dir data/generated/<run_id>

# Phase 2C — engineer behavioural features
.venv/Scripts/python -m features.feature_pipeline \
  --entities data/generated/<run_id>/entities.csv \
  --events data/attacks/<run_id>/events_injected.csv \
  --ground-truth data/attacks/<run_id>/ground_truth.csv

# Phase 3 — build behaviour profiles
.venv/Scripts/python -m profiles.behaviour_profile_engine \
  --entities data/generated/<run_id>/entities.csv \
  --events data/features/<run_id>/engineered_events.parquet
```

#### Detection Engine (Phase 4)

```bash
.venv/Scripts/python -m detection.detection_engine \
  --events data/features/<run_id>/engineered_events.parquet \
  --profile-store data/profiles/store \
  --output-dir data/detections \
  --scoring-strategy weighted_average
```

#### Classification Engine (Phase 5)

```bash
.venv/Scripts/python -m classification.classification_engine \
  --detection-results data/detections/<run_id>/detection_results.csv \
  --events data/features/<run_id>/engineered_events.parquet \
  --profile-store data/profiles/store \
  --output-dir data/classifications \
  --classification-strategy rule_based
```

#### Explainability Engine (Phase 6)

```bash
.venv/Scripts/python -m explainability.explainability_engine \
  --classification-results data/classifications/<run_id>/classification_report.csv \
  --detection-results data/detections/<run_id>/detection_results.csv \
  --events data/features/<run_id>/engineered_events.parquet \
  --profile-store data/profiles/store \
  --output-dir data/explainability
```

#### Dashboard Data Export

Run this before starting the frontend (Phase 7) or Phase 8's `--frontend-data-dir` benchmark — it builds the static fixtures both of them read.

```bash
.venv/Scripts/python -m dashboard_export.dashboard_export_engine \
  --detection-results data/detections/<run_id>/detection_results.csv \
  --classification-results data/classifications/<run_id>/classification_report.csv \
  --explainability-dir data/explainability/<run_id> \
  --events data/features/<run_id>/engineered_events.parquet \
  --entities data/generated/<run_id>/entities.csv \
  --profile-store data/profiles/store \
  --output-dir ../frontend/public/data
```

#### Enterprise Evaluation Framework (Phase 8)

```bash
.venv/Scripts/python -m evaluation.evaluation_engine \
  --detection-results data/detections/<run_id>/detection_results.csv \
  --classification-results data/classifications/<run_id>/classification_report.csv \
  --events data/features/<run_id>/engineered_events.parquet \
  --profile-store data/profiles/store \
  --frontend-data-dir ../frontend/public/data \
  --output-dir data/evaluation
```

See [ai-engine/README.md](ai-engine/README.md) for the full command reference, configuration options, and output schemas for every phase.

---

## Roadmap

Realistic, planned next steps — nothing below is implemented yet:

- **ML-based attack classification** — replace/augment the current rule-based `ClassificationStrategy` with a trained multi-class model, using the existing strategy interface
- **Real-time streaming ingestion** — connect `StreamProcessor` to a live event source instead of replaying historical files
- **Advanced threat intelligence enrichment** — augment MITRE mapping with external threat-intel context
- **Live backend domain API** — real endpoints for alerts, entities, and analytics backed by the database, replacing the current static-fixture data path (`GET /api/v1/health` is the only endpoint today)
- **Production deployment** — hardened, cloud-hosted deployment of the backend/frontend stack, including a production frontend build (the current Docker image runs Vite's development server, not a static build)
- **Model monitoring** — drift and performance monitoring for any trained model introduced above

---

## Design Tokens

| Token | Value |
|---|---|
| Primary | `#001F3F` |
| Background | `#F8FAFC` |
| Accent | `#00C2A8` |
