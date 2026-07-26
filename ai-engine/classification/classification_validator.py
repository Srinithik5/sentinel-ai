from __future__ import annotations

from dataclasses import dataclass

from classification.attack_registry import ATTACK_REGISTRY, AttackType, get_attack_definition
from classification.classification_engine import ClassificationResult


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


def validate_confidence_ranges(results: list[ClassificationResult]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for result in results:
        if not 0.0 <= result.confidence <= 1.0:
            issues.append(
                ValidationIssue("confidence_ranges", "error", f"{result.event_id}: confidence={result.confidence} out of [0,1].")
            )
        for attack_type, score in result.all_scores.items():
            if not 0.0 <= score <= 1.0:
                issues.append(
                    ValidationIssue(
                        "confidence_ranges", "error", f"{result.event_id}: score for {attack_type}={score} out of [0,1]."
                    )
                )
    return issues


def validate_attack_type_registered(results: list[ClassificationResult]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for result in results:
        if result.attack_type not in ATTACK_REGISTRY:
            issues.append(
                ValidationIssue(
                    "attack_type_registered", "error", f"{result.event_id}: attack_type={result.attack_type} is not in ATTACK_REGISTRY."
                )
            )
    return issues


def validate_mitre_completeness(results: list[ClassificationResult]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for result in results:
        if not result.mitre_tactic or not result.mitre_technique:
            issues.append(
                ValidationIssue("mitre_completeness", "error", f"{result.event_id}: missing MITRE tactic or technique.")
            )
            continue
        expected = get_attack_definition(result.attack_type)
        if result.mitre_tactic != expected.mitre_tactic or result.mitre_technique != expected.mitre_technique:
            issues.append(
                ValidationIssue(
                    "mitre_completeness",
                    "error",
                    f"{result.event_id}: MITRE mapping ({result.mitre_tactic}/{result.mitre_technique}) "
                    f"does not match the registry for {result.attack_type.value} "
                    f"({expected.mitre_tactic}/{expected.mitre_technique}).",
                )
            )
    return issues


def validate_evidence_presence(results: list[ClassificationResult]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for result in results:
        if result.attack_type != AttackType.UNKNOWN and not result.evidence:
            issues.append(
                ValidationIssue(
                    "evidence_presence", "error", f"{result.event_id}: classified as {result.attack_type.value} with no supporting evidence."
                )
            )
    return issues


def validate_determinism(first_pass: list[ClassificationResult], second_pass: list[ClassificationResult]) -> list[ValidationIssue]:
    if len(first_pass) != len(second_pass):
        return [ValidationIssue("determinism", "error", "Result count differs between two runs on identical input.")]

    first_by_id = {result.event_id: result for result in first_pass}
    for result in second_pass:
        other = first_by_id.get(result.event_id)
        if other is None or other.attack_type != result.attack_type or other.confidence != result.confidence:
            return [ValidationIssue("determinism", "error", f"Non-deterministic result for event {result.event_id}.")]
    return []


def run_all_classification_validations(results: list[ClassificationResult]) -> ValidationReport:
    issues: list[ValidationIssue] = []
    issues.extend(validate_confidence_ranges(results))
    issues.extend(validate_attack_type_registered(results))
    issues.extend(validate_mitre_completeness(results))
    issues.extend(validate_evidence_presence(results))
    return ValidationReport(issues=tuple(issues))