from __future__ import annotations

from dataclasses import dataclass

from classification.attack_registry import get_attack_definition
from classification.attack_registry import AttackType
from explainability.explainability_engine import ExplainabilityResult


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


def validate_contribution_percentages(results: list[ExplainabilityResult]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for result in results:
        total = round(sum(c.contribution_percentage for c in result.contributions), 2)
        if abs(total - 100.0) > 0.05:
            issues.append(
                ValidationIssue(
                    "contribution_percentages", "error", f"{result.event_id}: contribution percentages sum to {total}, expected 100.0."
                )
            )
        for contribution in result.contributions:
            if not 0.0 <= contribution.contribution_percentage <= 100.0:
                issues.append(
                    ValidationIssue(
                        "contribution_percentages",
                        "error",
                        f"{result.event_id}: {contribution.dimension} contribution={contribution.contribution_percentage} out of [0,100].",
                    )
                )
    return issues


def validate_confidence_level_consistency(results: list[ExplainabilityResult]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for result in results:
        confidence = result.evidence.classification.confidence
        if not 0.0 <= confidence <= 1.0:
            issues.append(
                ValidationIssue("confidence_level_consistency", "error", f"{result.event_id}: confidence={confidence} out of [0,1].")
            )
        if result.confidence_explanation.confidence != confidence:
            issues.append(
                ValidationIssue(
                    "confidence_level_consistency",
                    "error",
                    f"{result.event_id}: explained confidence {result.confidence_explanation.confidence} "
                    f"does not match Phase 5 confidence {confidence}.",
                )
            )
    return issues


def validate_recommendations_present(results: list[ExplainabilityResult]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for result in results:
        if not result.recommendations:
            issues.append(
                ValidationIssue("recommendations_present", "error", f"{result.event_id}: no recommended actions were generated.")
            )
        attack_type = AttackType(result.evidence.classification.attack_type)
        get_attack_definition(attack_type)  # raises KeyError if the attack type is unregistered
    return issues


def validate_narrative_completeness(results: list[ExplainabilityResult]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for result in results:
        narrative = result.narrative
        for field_name, value in narrative.to_dict().items():
            if not value or not str(value).strip():
                issues.append(
                    ValidationIssue("narrative_completeness", "error", f"{result.event_id}: narrative field '{field_name}' is empty.")
                )
    return issues


def validate_determinism(first_pass: list[ExplainabilityResult], second_pass: list[ExplainabilityResult]) -> list[ValidationIssue]:
    if len(first_pass) != len(second_pass):
        return [ValidationIssue("determinism", "error", "Result count differs between two runs on identical input.")]

    first_by_id = {result.event_id: result for result in first_pass}
    for result in second_pass:
        other = first_by_id.get(result.event_id)
        if (
            other is None
            or other.summary.to_dict() != result.summary.to_dict()
            or other.contributions != result.contributions
        ):
            return [ValidationIssue("determinism", "error", f"Non-deterministic result for event {result.event_id}.")]
    return []


def run_all_explainability_validations(results: list[ExplainabilityResult]) -> ValidationReport:
    issues: list[ValidationIssue] = []
    issues.extend(validate_contribution_percentages(results))
    issues.extend(validate_confidence_level_consistency(results))
    issues.extend(validate_recommendations_present(results))
    issues.extend(validate_narrative_completeness(results))
    return ValidationReport(issues=tuple(issues))