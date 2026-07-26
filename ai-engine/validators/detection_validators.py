from __future__ import annotations

from dataclasses import dataclass

from detection.decision_engine import DecisionEngine
from detection.detection_engine import DetectionResult
from detection.threshold_manager import ThresholdManager

_EXPECTED_DIMENSIONS: frozenset[str] = frozenset(
    {"temporal", "device", "resource", "geographic", "authentication", "session"}
)


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


def validate_score_ranges(results: list[DetectionResult]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for result in results:
        if not 0.0 <= result.anomaly_score <= 1.0:
            issues.append(
                ValidationIssue("score_ranges", "error", f"{result.event_id}: anomaly_score={result.anomaly_score} out of [0,1].")
            )
        if not 0.0 <= result.risk_assessment.risk_score <= 100.0:
            issues.append(
                ValidationIssue(
                    "score_ranges", "error", f"{result.event_id}: risk_score={result.risk_assessment.risk_score} out of [0,100]."
                )
            )
        for deviation in result.dimension_deviations:
            if not 0.0 <= deviation.deviation_score <= 1.0:
                issues.append(
                    ValidationIssue(
                        "score_ranges",
                        "error",
                        f"{result.event_id}: {deviation.dimension} deviation={deviation.deviation_score} out of [0,1].",
                    )
                )
    return issues


def validate_dimension_completeness(results: list[DetectionResult]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for result in results:
        found = {deviation.dimension for deviation in result.dimension_deviations}
        if found != _EXPECTED_DIMENSIONS:
            issues.append(
                ValidationIssue(
                    "dimension_completeness",
                    "error",
                    f"{result.event_id}: missing dimensions {_EXPECTED_DIMENSIONS - found}.",
                )
            )
    return issues


def validate_verdict_severity_consistency(
    results: list[DetectionResult], threshold_manager: ThresholdManager, decision_engine: DecisionEngine
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for result in results:
        expected_severity = threshold_manager.severity_for(result.risk_assessment.risk_score)
        expected_verdict = decision_engine.decide(result.risk_assessment.risk_score)
        if expected_severity != result.severity:
            issues.append(
                ValidationIssue(
                    "verdict_consistency",
                    "error",
                    f"{result.event_id}: severity {result.severity.value} inconsistent with risk_score "
                    f"{result.risk_assessment.risk_score} (expected {expected_severity.value}).",
                )
            )
        if expected_verdict != result.verdict:
            issues.append(
                ValidationIssue(
                    "verdict_consistency",
                    "error",
                    f"{result.event_id}: verdict {result.verdict.value} inconsistent with risk_score "
                    f"{result.risk_assessment.risk_score} (expected {expected_verdict.value}).",
                )
            )
    return issues


def validate_determinism(first_pass: list[DetectionResult], second_pass: list[DetectionResult]) -> list[ValidationIssue]:
    if len(first_pass) != len(second_pass):
        return [ValidationIssue("determinism", "error", "Result count differs between two runs on identical input.")]

    first_by_id = {result.event_id: result for result in first_pass}
    for result in second_pass:
        other = first_by_id.get(result.event_id)
        if (
            other is None
            or other.risk_assessment.risk_score != result.risk_assessment.risk_score
            or other.verdict != result.verdict
        ):
            return [ValidationIssue("determinism", "error", f"Non-deterministic result for event {result.event_id}.")]
    return []


def run_all_detection_validations(
    results: list[DetectionResult],
    *,
    threshold_manager: ThresholdManager | None = None,
    decision_engine: DecisionEngine | None = None,
) -> ValidationReport:
    issues: list[ValidationIssue] = []
    issues.extend(validate_score_ranges(results))
    issues.extend(validate_dimension_completeness(results))
    if threshold_manager is not None and decision_engine is not None:
        issues.extend(validate_verdict_severity_consistency(results, threshold_manager, decision_engine))
    return ValidationReport(issues=tuple(issues))