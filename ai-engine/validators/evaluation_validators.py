from __future__ import annotations

from dataclasses import dataclass

from evaluation.classification_metrics import ClassificationEvaluationResult
from evaluation.cold_start_evaluator import ColdStartEvaluationResult
from evaluation.concept_drift_evaluator import ConceptDriftEvaluationResult
from evaluation.detection_metrics import DetectionEvaluationResult
from evaluation.latency_benchmark import DashboardLatencyBenchmarkResult
from evaluation.scalability_benchmark import ScalabilityBenchmarkResult
from evaluation.streaming_benchmark import StreamingBenchmarkResult

_UNIT_METRICS = ("precision", "recall", "f1", "roc_auc", "pr_auc", "false_positive_rate", "false_negative_rate")


@dataclass(frozen=True)
class ValidationIssue:
    check: str
    severity: str  # "error" | "warning"
    message: str


@dataclass(frozen=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...]

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")


def _check_unit_interval(value: float, *, check: str, label: str) -> ValidationIssue | None:
    if not 0.0 <= value <= 1.0 + 1e-9:
        return ValidationIssue(check, "error", f"{label}={value} is outside the expected [0,1] range.")
    return None


def validate_detection_evaluation(result: DetectionEvaluationResult) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for label, value in (
        ("precision", result.confusion.precision),
        ("recall", result.confusion.recall),
        ("f1", result.confusion.f1),
        ("roc_auc", result.roc.auc),
        ("pr_auc", result.pr.auc),
        ("false_positive_rate", result.false_positive_rate),
        ("false_negative_rate", result.false_negative_rate),
        (f"top_{result.top_percentile:g}pct_precision", result.top_percentile_precision),
    ):
        issue = _check_unit_interval(value, check="detection_metric_range", label=label)
        if issue:
            issues.append(issue)

    total = result.confusion.total
    if total != result.labeled_count:
        issues.append(
            ValidationIssue(
                "detection_confusion_total", "error", f"Confusion matrix total {total} does not match labeled_count {result.labeled_count}."
            )
        )
    return issues


def validate_classification_evaluation(result: ClassificationEvaluationResult) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for label, value in (("macro_f1", result.macro_f1), ("weighted_f1", result.weighted_f1), ("overall_accuracy", result.overall_accuracy)):
        issue = _check_unit_interval(value, check="classification_metric_range", label=label)
        if issue:
            issues.append(issue)

    for item in result.per_class:
        for metric_label, value in (("precision", item.precision), ("recall", item.recall), ("f1", item.f1)):
            issue = _check_unit_interval(value, check="classification_per_class_range", label=f"{item.class_name}.{metric_label}")
            if issue:
                issues.append(issue)

    matrix_total = sum(sum(row.values()) for row in result.confusion_matrix.values())
    if matrix_total != result.labeled_count:
        issues.append(
            ValidationIssue(
                "classification_confusion_total",
                "error",
                f"Confusion matrix total {matrix_total} does not match labeled_count {result.labeled_count}.",
            )
        )
    return issues


def validate_cold_start_evaluation(result: ColdStartEvaluationResult) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for segment in result.segments:
        if not 0.0 <= segment.flagged_rate <= 1.0:
            issues.append(
                ValidationIssue("cold_start_flagged_rate", "error", f"{segment.segment_name}: flagged_rate={segment.flagged_rate} out of [0,1].")
            )
        if segment.false_positive_rate is not None and not 0.0 <= segment.false_positive_rate <= 1.0:
            issues.append(
                ValidationIssue(
                    "cold_start_false_positive_rate",
                    "error",
                    f"{segment.segment_name}: false_positive_rate={segment.false_positive_rate} out of [0,1].",
                )
            )
    for bucket in result.warmup_curve:
        if not 0.0 <= bucket.avg_historical_confidence <= 1.0:
            issues.append(
                ValidationIssue(
                    "cold_start_warmup_confidence",
                    "error",
                    f"{bucket.history_length_range}: avg_historical_confidence={bucket.avg_historical_confidence} out of [0,1].",
                )
            )
    for calibration_bin in result.calibration_curve:
        if calibration_bin.empirical_accuracy is not None and not 0.0 <= calibration_bin.empirical_accuracy <= 1.0:
            issues.append(
                ValidationIssue(
                    "cold_start_calibration_accuracy",
                    "error",
                    f"{calibration_bin.confidence_range}: empirical_accuracy={calibration_bin.empirical_accuracy} out of [0,1].",
                )
            )
    return issues


def validate_concept_drift_evaluation(result: ConceptDriftEvaluationResult) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not result.weekly_drift:
        issues.append(ValidationIssue("concept_drift_weekly_present", "error", "No weekly drift periods were computed."))
    if not result.monthly_drift:
        issues.append(ValidationIssue("concept_drift_monthly_present", "error", "No monthly drift periods were computed."))
    for period in (*result.weekly_drift, *result.monthly_drift):
        if not 0.0 <= period.avg_drift_score <= 1.0:
            issues.append(
                ValidationIssue("concept_drift_score_range", "error", f"{period.period_label}: avg_drift_score={period.avg_drift_score} out of [0,1].")
            )
    if result.profile_updates.entities_with_multiple_versions > result.profile_updates.total_entities:
        issues.append(
            ValidationIssue(
                "concept_drift_profile_updates", "error", "entities_with_multiple_versions exceeds total_entities."
            )
        )
    return issues


def validate_scalability_benchmark(result: ScalabilityBenchmarkResult) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for tier in result.tiers:
        if tier.event_count <= 0:
            issues.append(ValidationIssue("scalability_event_count", "error", f"Tier {tier.target_entity_count}: no events were processed."))
        if tier.total_seconds < 0 or tier.avg_latency_ms < 0 or tier.cpu_seconds < 0 or tier.peak_memory_mb < 0:
            issues.append(ValidationIssue("scalability_negative_measurement", "error", f"Tier {tier.target_entity_count}: a timing/resource measurement was negative."))
        if tier.real_entity_count + tier.synthetic_entity_count != tier.target_entity_count:
            issues.append(
                ValidationIssue(
                    "scalability_entity_count_consistency",
                    "error",
                    f"Tier {tier.target_entity_count}: real ({tier.real_entity_count}) + synthetic ({tier.synthetic_entity_count}) does not equal target.",
                )
            )
    return issues


def validate_streaming_benchmark(result: StreamingBenchmarkResult) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if result.event_count <= 0:
        issues.append(ValidationIssue("streaming_event_count", "error", "No events were processed by the streaming benchmark."))
    if result.worst_latency_ms < result.p99_latency_ms - 1e-6:
        issues.append(ValidationIssue("streaming_percentile_ordering", "error", "worst_latency_ms is less than p99_latency_ms."))
    if result.p99_latency_ms < result.p95_latency_ms - 1e-6:
        issues.append(ValidationIssue("streaming_percentile_ordering", "error", "p99_latency_ms is less than p95_latency_ms."))
    if result.p95_latency_ms < result.p50_latency_ms - 1e-6:
        issues.append(ValidationIssue("streaming_percentile_ordering", "error", "p95_latency_ms is less than p50_latency_ms."))
    return issues


def validate_dashboard_latency_benchmark(result: DashboardLatencyBenchmarkResult) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not result.api_latency:
        issues.append(ValidationIssue("dashboard_api_latency_present", "error", "No dashboard fixtures were benchmarked."))
    for entry in result.api_latency:
        if entry.payload_bytes <= 0:
            issues.append(ValidationIssue("dashboard_payload_size", "error", f"{entry.fixture_name}: payload_bytes must be positive."))
    if result.search_latency.dataset_size <= 0:
        issues.append(ValidationIssue("dashboard_search_dataset", "error", "Search latency benchmark ran against an empty alert dataset."))
    return issues


def run_all_evaluation_validations(
    *,
    detection: DetectionEvaluationResult,
    classification: ClassificationEvaluationResult,
    cold_start: ColdStartEvaluationResult,
    concept_drift: ConceptDriftEvaluationResult,
    scalability: ScalabilityBenchmarkResult,
    streaming: StreamingBenchmarkResult,
    dashboard_latency: DashboardLatencyBenchmarkResult,
) -> ValidationReport:
    issues: list[ValidationIssue] = []
    issues.extend(validate_detection_evaluation(detection))
    issues.extend(validate_classification_evaluation(classification))
    issues.extend(validate_cold_start_evaluation(cold_start))
    issues.extend(validate_concept_drift_evaluation(concept_drift))
    issues.extend(validate_scalability_benchmark(scalability))
    issues.extend(validate_streaming_benchmark(streaming))
    issues.extend(validate_dashboard_latency_benchmark(dashboard_latency))
    return ValidationReport(issues=tuple(issues))