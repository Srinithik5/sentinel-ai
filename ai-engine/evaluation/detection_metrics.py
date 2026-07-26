from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from evaluation.metrics_engine import (
    ConfusionCounts,
    CurveResult,
    compute_confusion_counts,
    compute_pr_curve,
    compute_roc_curve,
    top_percentile_precision,
)

_TOP_PERCENTILE = 1.0


@dataclass(frozen=True)
class DetectionEvaluationResult:
    """The required Detection Evaluation metrics, computed independently
    from Phase 4's own `detection_results.csv` — this framework never
    reads Phase 4's own precomputed `detection_metrics.md`, it recomputes
    from the raw per-event rows so the evaluation is a genuine, separate
    check rather than an echo of numbers Phase 4 already printed.
    """

    sample_count: int
    labeled_count: int
    confusion: ConfusionCounts
    roc: CurveResult
    pr: CurveResult
    false_positive_rate: float
    false_negative_rate: float
    top_percentile: float
    top_percentile_precision: float
    top_percentile_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "sample_count": self.sample_count,
            "labeled_count": self.labeled_count,
            "precision": self.confusion.precision,
            "recall": self.confusion.recall,
            "f1": self.confusion.f1,
            "roc_auc": self.roc.auc,
            "pr_auc": self.pr.auc,
            "false_positive_rate": self.false_positive_rate,
            "false_negative_rate": self.false_negative_rate,
            f"top_{self.top_percentile:g}pct_precision": self.top_percentile_precision,
            f"top_{self.top_percentile:g}pct_count": self.top_percentile_count,
        }


class DetectionEvaluator:
    """Computes Precision, Recall, F1, ROC-AUC, PR-AUC, False Positive
    Rate, False Negative Rate, and top-1% analyst-alert precision from a
    Phase 4 `detection_results.csv`/`.parquet` file. Every metric is
    derived via `metrics_engine`'s shared primitives — no metric math is
    reimplemented here.
    """

    def __init__(self, *, top_percentile: float = _TOP_PERCENTILE) -> None:
        self.top_percentile = top_percentile

    def evaluate(self, detection_df: pd.DataFrame) -> DetectionEvaluationResult:
        labeled = detection_df[detection_df["is_attack"].notna()].copy()
        if labeled.empty:
            raise ValueError("No labeled rows (is_attack) found in detection results — cannot evaluate.")

        y_true = labeled["is_attack"].astype(bool).to_numpy()
        y_pred = (labeled["verdict"] != "normal").to_numpy()
        y_score = labeled["risk_score"].astype(float).to_numpy()

        confusion = compute_confusion_counts(y_true, y_pred)
        roc = compute_roc_curve(y_true, y_score)
        pr = compute_pr_curve(y_true, y_score)
        top_precision, top_count = top_percentile_precision(y_true, y_score, self.top_percentile)

        return DetectionEvaluationResult(
            sample_count=len(detection_df),
            labeled_count=len(labeled),
            confusion=confusion,
            roc=roc,
            pr=pr,
            false_positive_rate=confusion.false_positive_rate,
            false_negative_rate=confusion.false_negative_rate,
            top_percentile=self.top_percentile,
            top_percentile_precision=top_precision,
            top_percentile_count=top_count,
        )


def load_detection_results(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, low_memory=False)
    required = {"event_id", "entity_id", "risk_score", "verdict", "is_attack"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"detection results file is missing required columns: {sorted(missing)}")
    if df["is_attack"].dtype == object:
        df["is_attack"] = df["is_attack"].map({"True": True, "False": False, True: True, False: False, np.nan: np.nan})
    return df