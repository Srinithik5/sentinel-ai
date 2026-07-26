from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from evaluation.metrics_engine import (
    PerClassCounts,
    compute_multiclass_confusion,
    macro_f1,
    per_class_metrics,
    weighted_f1,
)


@dataclass(frozen=True)
class ClassificationEvaluationResult:
    """The required Classification Evaluation outputs, computed
    independently from Phase 5's `classification_report.csv` against the
    subset of events with real ground-truth attack types.
    """

    labeled_count: int
    classes: tuple[str, ...]
    confusion_matrix: dict[str, dict[str, int]]
    per_class: tuple[PerClassCounts, ...]
    macro_f1: float
    weighted_f1: float
    overall_accuracy: float

    def to_dict(self) -> dict[str, object]:
        return {
            "labeled_count": self.labeled_count,
            "classes": list(self.classes),
            "macro_f1": self.macro_f1,
            "weighted_f1": self.weighted_f1,
            "overall_accuracy": self.overall_accuracy,
            "per_class": [
                {
                    "class_name": item.class_name,
                    "support": item.support,
                    "precision": item.precision,
                    "recall": item.recall,
                    "f1": item.f1,
                }
                for item in self.per_class
            ],
        }


class ClassificationEvaluator:
    """Computes the confusion matrix and per-class/macro/weighted metrics
    for Phase 5's attack-type classification. Every metric is derived via
    `metrics_engine`'s shared multiclass primitives.
    """

    def evaluate(self, classification_df: pd.DataFrame) -> ClassificationEvaluationResult:
        labeled = classification_df[classification_df["ground_truth_attack_type"].notna()].copy()
        if labeled.empty:
            raise ValueError("No labeled rows (ground_truth_attack_type) found in classification results.")

        y_true = labeled["ground_truth_attack_type"].astype(str).tolist()
        y_pred = labeled["attack_type"].astype(str).tolist()
        classes = sorted(set(y_true) | set(y_pred))

        matrix = compute_multiclass_confusion(y_true, y_pred, classes)
        per_class = per_class_metrics(matrix, classes)
        correct = sum(1 for actual, predicted in zip(y_true, y_pred) if actual == predicted)
        overall_accuracy = round(correct / len(labeled), 6)

        return ClassificationEvaluationResult(
            labeled_count=len(labeled),
            classes=tuple(classes),
            confusion_matrix=matrix,
            per_class=per_class,
            macro_f1=macro_f1(per_class),
            weighted_f1=weighted_f1(per_class),
            overall_accuracy=overall_accuracy,
        )


def load_classification_results(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, low_memory=False)
    required = {"event_id", "entity_id", "attack_type", "ground_truth_attack_type"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"classification results file is missing required columns: {sorted(missing)}")
    return df