from __future__ import annotations

from dataclasses import dataclass

from profiles.profile_manager import BehaviourProfile


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


def validate_probability_distributions(profile: BehaviourProfile) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    for name, distribution in (
        ("resource_frequency", profile.statistical.resource_frequency),
        ("device_frequency", profile.statistical.device_frequency),
        ("geo_frequency", profile.statistical.geo_frequency),
    ):
        if not distribution:
            continue
        total = sum(distribution.values())
        if abs(total - 1.0) > 0.01:
            issues.append(
                ValidationIssue(
                    "probability_distributions",
                    "error",
                    f"{profile.entity_id}: statistical.{name} sums to {total:.4f}, expected ~1.0.",
                )
            )

    for matrix_name, matrix in (
        ("command_transition_matrix", profile.sequence.command_transition_matrix),
        ("resource_transition_matrix", profile.sequence.resource_transition_matrix),
    ):
        for state, transitions in matrix.items():
            total = sum(transitions.values())
            if abs(total - 1.0) > 0.01:
                issues.append(
                    ValidationIssue(
                        "probability_distributions",
                        "error",
                        f"{profile.entity_id}: sequence.{matrix_name}['{state}'] sums to {total:.4f}, expected ~1.0.",
                    )
                )

    return issues


def validate_value_ranges(profile: BehaviourProfile) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    checks: tuple[tuple[str, float], ...] = (
        ("statistical.failure_rate", profile.statistical.failure_rate),
        ("statistical.working_hour_ratio", profile.statistical.working_hour_ratio),
        ("relationship.resource_sharing_score", profile.relationship.resource_sharing_score),
        ("drift.drift_score", profile.drift.drift_score),
        ("cold_start.confidence_score", profile.cold_start.confidence_score),
    )
    for field_name, value in checks:
        if not 0.0 <= value <= 1.0:
            issues.append(
                ValidationIssue("value_ranges", "error", f"{profile.entity_id}: {field_name}={value} out of [0.0, 1.0].")
            )

    if profile.version < 1:
        issues.append(
            ValidationIssue("value_ranges", "error", f"{profile.entity_id}: version must be >= 1, got {profile.version}.")
        )

    return issues


def validate_version_monotonicity(profile: BehaviourProfile, previous_version: int | None) -> list[ValidationIssue]:
    if previous_version is not None and profile.version <= previous_version:
        return [
            ValidationIssue(
                "version_monotonicity",
                "error",
                f"{profile.entity_id}: new version {profile.version} is not greater than previous version {previous_version}.",
            )
        ]
    return []


def validate_entity_consistency(profiles: list[BehaviourProfile], known_entity_ids: set[str]) -> list[ValidationIssue]:
    orphaned = [profile.entity_id for profile in profiles if profile.entity_id not in known_entity_ids]
    if orphaned:
        preview = sorted(orphaned)[:5]
        return [
            ValidationIssue(
                "entity_consistency",
                "error",
                f"{len(orphaned)} profiled entities are not present in entities.csv: {preview}"
                f"{'...' if len(orphaned) > 5 else ''}",
            )
        ]
    return []


def run_all_profile_validations(
    profiles: list[BehaviourProfile],
    *,
    known_entity_ids: set[str],
    previous_versions: dict[str, int],
) -> ValidationReport:
    issues: list[ValidationIssue] = []
    issues.extend(validate_entity_consistency(profiles, known_entity_ids))
    for profile in profiles:
        issues.extend(validate_probability_distributions(profile))
        issues.extend(validate_value_ranges(profile))
        issues.extend(validate_version_monotonicity(profile, previous_versions.get(profile.entity_id)))
    return ValidationReport(issues=tuple(issues))