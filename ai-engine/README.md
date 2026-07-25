# AI Engine

Model development workspace for SentinelAI's behavioral anomaly detection models.

## Structure

- `data/` — raw and processed datasets (not committed; see `.gitignore`).
- `models/` — trained model artifacts and checkpoints.
- `notebooks/` — exploratory analysis and experimentation notebooks.
- `src/preprocessing/` — feature engineering and data pipeline code.
- `src/training/` — model training scripts.
- `src/inference/` — inference/serving code.
- `src/explainability/` — SHAP-based explainability tooling.
- `src/evaluation/` — model evaluation and metrics.

This module is scaffolding only in Phase 1. No models, training, or detection logic are implemented yet.