from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from features.feature_registry import FEATURE_REGISTRY


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


_RATIO_FEATURES: tuple[str, ...] = (
    "success_ratio",
    "failure_ratio",
    "mfa_usage_frequency",
    "resource_diversity",
    "city_change_frequency",
    "confidence_score",
    "command_sequence_complexity",
    "device_familiarity_score",
    "behaviour_drift_score",
)
_BOOLEAN_FEATURES: tuple[str, ...] = (
    "is_weekend",
    "geo_novelty",
    "country_change",
    "fingerprint_mismatch",
    "os_novelty",
    "mac_novelty",
    "resource_novelty",
    "privilege_change_indicator",
    "sensitive_resource_access",
    "new_entity_flag",
)


def validate_schema_completeness(df: pd.DataFrame) -> list[ValidationIssue]:
    missing = [feature.name for feature in FEATURE_REGISTRY if feature.name not in df.columns]
    if missing:
        return [ValidationIssue("schema_completeness", "error", f"Missing registered features: {missing}")]
    return []


def validate_row_count(df: pd.DataFrame, expected_row_count: int) -> list[ValidationIssue]:
    if len(df) != expected_row_count:
        return [
            ValidationIssue(
                "row_count",
                "error",
                f"Engineered dataset has {len(df)} rows, expected {expected_row_count} (one per input event) — "
                f"a merge likely duplicated or dropped rows.",
            )
        ]
    return []


def validate_no_unexpected_nulls(df: pd.DataFrame) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for feature in FEATURE_REGISTRY:
        if feature.name not in df.columns:
            continue
        null_count = int(df[feature.name].isna().sum())
        if null_count > 0:
            issues.append(
                ValidationIssue(
                    "no_unexpected_nulls",
                    "error",
                    f"Feature '{feature.name}' has {null_count} null values; every feature must be well-defined "
                    f"via a sentinel value for cold-start cases, never NaN.",
                )
            )
    return issues


def validate_value_ranges(df: pd.DataFrame) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if "login_hour" in df.columns and not df["login_hour"].between(0, 23).all():
        issues.append(ValidationIssue("value_ranges", "error", "login_hour has values outside [0, 23]."))
    if "day_of_week" in df.columns and not df["day_of_week"].between(0, 6).all():
        issues.append(ValidationIssue("value_ranges", "error", "day_of_week has values outside [0, 6]."))
    if "historical_percentile_session_duration" in df.columns and not df[
        "historical_percentile_session_duration"
    ].between(0.0, 100.0).all():
        issues.append(
            ValidationIssue(
                "value_ranges", "error", "historical_percentile_session_duration has values outside [0, 100]."
            )
        )

    for name in _RATIO_FEATURES:
        if name in df.columns and not df[name].between(0.0, 1.0).all():
            issues.append(ValidationIssue("value_ranges", "error", f"'{name}' has values outside [0.0, 1.0]."))

    for name in _BOOLEAN_FEATURES:
        if name in df.columns and not df[name].isin([True, False]).all():
            issues.append(ValidationIssue("value_ranges", "error", f"'{name}' has non-boolean values."))

    return issues


def validate_determinism(first_pass: pd.DataFrame, second_pass: pd.DataFrame) -> list[ValidationIssue]:
    feature_columns = [feature.name for feature in FEATURE_REGISTRY]
    left = first_pass.sort_values("event_id").reset_index(drop=True)[["event_id", *feature_columns]]
    right = second_pass.sort_values("event_id").reset_index(drop=True)[["event_id", *feature_columns]]
    if not left.equals(right):
        return [
            ValidationIssue(
                "determinism", "error", "Re-running the pipeline on identical input produced different feature values."
            )
        ]
    return []


def run_all_feature_validations(df: pd.DataFrame, *, expected_row_count: int) -> ValidationReport:
    issues: list[ValidationIssue] = []
    issues.extend(validate_schema_completeness(df))
    issues.extend(validate_row_count(df, expected_row_count))
    issues.extend(validate_no_unexpected_nulls(df))
    issues.extend(validate_value_ranges(df))
    return ValidationReport(issues=tuple(issues))