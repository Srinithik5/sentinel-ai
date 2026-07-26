from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

BoolArray = npt.NDArray[np.bool_]
FloatArray = npt.NDArray[np.float64]


@dataclass(frozen=True)
class ConfusionCounts:
    """The four counts every binary classification metric is built from.
    Every derived property below is a pure function of these four numbers
    — no recomputation of the underlying predictions anywhere else in the
    evaluation framework.
    """

    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int

    @property
    def total(self) -> int:
        return self.true_positive + self.false_positive + self.true_negative + self.false_negative

    @property
    def positives(self) -> int:
        return self.true_positive + self.false_negative

    @property
    def negatives(self) -> int:
        return self.false_positive + self.true_negative

    @property
    def precision(self) -> float:
        denominator = self.true_positive + self.false_positive
        return round(self.true_positive / denominator, 6) if denominator else 0.0

    @property
    def recall(self) -> float:
        denominator = self.true_positive + self.false_negative
        return round(self.true_positive / denominator, 6) if denominator else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return round(2 * p * r / (p + r), 6) if (p + r) else 0.0

    @property
    def false_positive_rate(self) -> float:
        denominator = self.false_positive + self.true_negative
        return round(self.false_positive / denominator, 6) if denominator else 0.0

    @property
    def false_negative_rate(self) -> float:
        denominator = self.false_negative + self.true_positive
        return round(self.false_negative / denominator, 6) if denominator else 0.0

    @property
    def accuracy(self) -> float:
        return round((self.true_positive + self.true_negative) / self.total, 6) if self.total else 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "true_positive": self.true_positive,
            "false_positive": self.false_positive,
            "true_negative": self.true_negative,
            "false_negative": self.false_negative,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "false_positive_rate": self.false_positive_rate,
            "false_negative_rate": self.false_negative_rate,
            "accuracy": self.accuracy,
        }


def compute_confusion_counts(y_true: BoolArray, y_pred: BoolArray) -> ConfusionCounts:
    """Builds a ConfusionCounts from two parallel boolean arrays. Pure,
    deterministic, and the single place every binary evaluation in this
    framework derives its confusion matrix from.
    """
    if len(y_true) != len(y_pred):
        raise ValueError(f"y_true and y_pred must be the same length, got {len(y_true)} and {len(y_pred)}")

    y_true = np.asarray(y_true, dtype=bool)
    y_pred = np.asarray(y_pred, dtype=bool)

    return ConfusionCounts(
        true_positive=int(np.sum(y_true & y_pred)),
        false_positive=int(np.sum(~y_true & y_pred)),
        true_negative=int(np.sum(~y_true & ~y_pred)),
        false_negative=int(np.sum(y_true & ~y_pred)),
    )


@dataclass(frozen=True)
class CurvePoint:
    threshold: float
    x: float
    y: float

    def to_dict(self) -> dict[str, object]:
        return {"threshold": self.threshold, "x": self.x, "y": self.y}


@dataclass(frozen=True)
class CurveResult:
    """A sampled curve (ROC or PR) plus its area under the curve. `points`
    is downsampled to at most `max_points` for reporting — the AUC itself
    is always computed from the full, un-downsampled data.
    """

    points: tuple[CurvePoint, ...]
    auc: float

    def to_dict(self) -> dict[str, object]:
        return {"auc": self.auc, "points": [point.to_dict() for point in self.points]}


_MAX_CURVE_POINTS = 200


def _downsample(values: FloatArray, max_points: int) -> FloatArray:
    if len(values) <= max_points:
        return np.arange(len(values))
    return np.linspace(0, len(values) - 1, max_points).round().astype(int)


def compute_roc_curve(y_true: BoolArray, y_score: FloatArray) -> CurveResult:
    """Computes the ROC curve and its AUC via the trapezoidal rule.
    Deterministic and dependency-free beyond NumPy — no scikit-learn.
    """
    y_true = np.asarray(y_true, dtype=bool)
    y_score = np.asarray(y_score, dtype=float)

    order = np.argsort(-y_score, kind="stable")
    y_true_sorted = y_true[order]
    score_sorted = y_score[order]

    positives = int(y_true_sorted.sum())
    negatives = len(y_true_sorted) - positives
    if positives == 0 or negatives == 0:
        raise ValueError("ROC curve requires at least one positive and one negative example.")

    tp_cumulative = np.cumsum(y_true_sorted)
    fp_cumulative = np.cumsum(~y_true_sorted)
    tpr = tp_cumulative / positives
    fpr = fp_cumulative / negatives

    fpr = np.concatenate(([0.0], fpr))
    tpr = np.concatenate(([0.0], tpr))
    thresholds = np.concatenate(([score_sorted[0] + 1.0], score_sorted))

    auc = float(np.trapezoid(tpr, fpr))

    sample_idx = _downsample(fpr, _MAX_CURVE_POINTS)
    points = tuple(
        CurvePoint(threshold=round(float(thresholds[i]), 4), x=round(float(fpr[i]), 6), y=round(float(tpr[i]), 6))
        for i in sample_idx
    )
    return CurveResult(points=points, auc=round(auc, 6))


def compute_pr_curve(y_true: BoolArray, y_score: FloatArray) -> CurveResult:
    """Computes the Precision-Recall curve and its AUC via the average-
    precision formula (sum of (recall_i - recall_{i-1}) * precision_i) —
    the same standard, step-wise definition scikit-learn's
    `average_precision_score` uses, avoiding the interpolation artifacts a
    naive trapezoidal rule produces on PR curves.
    """
    y_true = np.asarray(y_true, dtype=bool)
    y_score = np.asarray(y_score, dtype=float)

    order = np.argsort(-y_score, kind="stable")
    y_true_sorted = y_true[order]
    score_sorted = y_score[order]

    positives = int(y_true_sorted.sum())
    if positives == 0:
        raise ValueError("PR curve requires at least one positive example.")

    tp_cumulative = np.cumsum(y_true_sorted)
    fp_cumulative = np.cumsum(~y_true_sorted)
    precision = tp_cumulative / (tp_cumulative + fp_cumulative)
    recall = tp_cumulative / positives

    recall_prev = np.concatenate(([0.0], recall[:-1]))
    average_precision = float(np.sum((recall - recall_prev) * precision))

    sample_idx = _downsample(recall, _MAX_CURVE_POINTS)
    points = tuple(
        CurvePoint(
            threshold=round(float(score_sorted[i]), 4), x=round(float(recall[i]), 6), y=round(float(precision[i]), 6)
        )
        for i in sample_idx
    )
    return CurveResult(points=points, auc=round(average_precision, 6))


def top_percentile_precision(y_true: BoolArray, y_score: FloatArray, percentile: float) -> tuple[float, int]:
    """Precision within the top `percentile`% of events by score — the
    "if an analyst can only review the riskiest slice, how precise is it"
    metric. Returns (precision, subset_size).
    """
    if not 0.0 < percentile <= 100.0:
        raise ValueError(f"percentile must be in (0, 100], got {percentile}")

    y_true = np.asarray(y_true, dtype=bool)
    y_score = np.asarray(y_score, dtype=float)

    subset_size = max(1, round(len(y_score) * percentile / 100))
    order = np.argsort(-y_score, kind="stable")[:subset_size]
    precision = float(np.sum(y_true[order])) / subset_size
    return round(precision, 6), subset_size


@dataclass(frozen=True)
class PerClassCounts:
    class_name: str
    support: int
    confusion: ConfusionCounts

    @property
    def precision(self) -> float:
        return self.confusion.precision

    @property
    def recall(self) -> float:
        return self.confusion.recall

    @property
    def f1(self) -> float:
        return self.confusion.f1


def compute_multiclass_confusion(y_true: list[str], y_pred: list[str], classes: list[str]) -> dict[str, dict[str, int]]:
    """Builds an actual-vs-predicted count matrix for an arbitrary set of
    class labels — the multiclass analogue of `compute_confusion_counts`.
    """
    matrix: dict[str, dict[str, int]] = {actual: {predicted: 0 for predicted in classes} for actual in classes}
    for actual, predicted in zip(y_true, y_pred):
        matrix[actual][predicted] += 1
    return matrix


def per_class_metrics(matrix: dict[str, dict[str, int]], classes: list[str]) -> tuple[PerClassCounts, ...]:
    """Derives one-vs-rest ConfusionCounts (and therefore precision/recall/
    F1) for every class directly from the multiclass confusion matrix —
    the standard sklearn-style per-class breakdown.
    """
    results: list[PerClassCounts] = []
    for class_name in classes:
        true_positive = matrix[class_name][class_name]
        false_negative = sum(matrix[class_name][other] for other in classes if other != class_name)
        false_positive = sum(matrix[other][class_name] for other in classes if other != class_name)
        support = true_positive + false_negative
        total = sum(sum(row.values()) for row in matrix.values())
        true_negative = total - true_positive - false_negative - false_positive
        confusion = ConfusionCounts(
            true_positive=true_positive, false_positive=false_positive, true_negative=true_negative, false_negative=false_negative
        )
        results.append(PerClassCounts(class_name=class_name, support=support, confusion=confusion))
    return tuple(results)


def macro_f1(per_class: tuple[PerClassCounts, ...]) -> float:
    if not per_class:
        return 0.0
    return round(sum(item.f1 for item in per_class) / len(per_class), 6)


def weighted_f1(per_class: tuple[PerClassCounts, ...]) -> float:
    total_support = sum(item.support for item in per_class)
    if total_support == 0:
        return 0.0
    return round(sum(item.f1 * item.support for item in per_class) / total_support, 6)