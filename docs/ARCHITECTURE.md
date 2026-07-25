# SentinelAI — Architecture (Phase 1)

## Overview

SentinelAI is split into three independently deployable services plus a shared contracts package:

```mermaid
graph LR
    FE[frontend<br/>React + Vite] -- HTTPS/JSON --> BE[backend<br/>FastAPI]
    BE -- SQLAlchemy --> DB[(PostgreSQL)]
    BE -. future phase .-> AI[ai-engine<br/>PyTorch / scikit-learn]
    FE -. types .-> SH[shared]
    BE -. schemas .-> SH