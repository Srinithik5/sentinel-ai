from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from attacks.base import INJECTED_EVENT_COLUMNS


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


def validate_attack_percentage(total_events: int, injected_event_count: int, max_percentage: float) -> list[ValidationIssue]:
    if total_events == 0:
        return [ValidationIssue("attack_percentage", "error", "No events found in the merged dataset.")]

    percentage = injected_event_count / total_events
    if percentage > max_percentage:
        return [
            ValidationIssue(
                "attack_percentage",
                "warning",
                f"Injected events make up {percentage:.2%} of the dataset, exceeding the configured "
                f"maximum of {max_percentage:.2%}.",
            )
        ]
    return []


def validate_dataset_integrity(merged_df: pd.DataFrame) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    missing_columns = [column for column in INJECTED_EVENT_COLUMNS if column not in merged_df.columns]
    if missing_columns:
        issues.append(
            ValidationIssue("dataset_integrity", "error", f"Merged dataset is missing required columns: {missing_columns}")
        )
        return issues

    if merged_df["event_id"].isna().any():
        issues.append(ValidationIssue("dataset_integrity", "error", "Found rows with a null event_id."))

    duplicate_count = int(merged_df["event_id"].duplicated().sum())
    if duplicate_count > 0:
        issues.append(ValidationIssue("dataset_integrity", "error", f"Found {duplicate_count} duplicate event_id values."))

    if merged_df["entity_id"].isna().any():
        issues.append(ValidationIssue("dataset_integrity", "error", "Found rows with a null entity_id."))

    return issues


def validate_chronological_consistency(merged_df: pd.DataFrame, start_date: date, end_date: date) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    timestamps = pd.to_datetime(merged_df["timestamp"], format="ISO8601")

    range_start = pd.Timestamp(start_date, tz="UTC")
    range_end = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1)

    out_of_range_count = int(((timestamps < range_start) | (timestamps >= range_end)).sum())
    if out_of_range_count > 0:
        issues.append(
            ValidationIssue(
                "chronological_consistency",
                "error",
                f"Found {out_of_range_count} events with timestamps outside the dataset's date range "
                f"({start_date} to {end_date}).",
            )
        )

    return issues


def validate_entity_consistency(entities_df: pd.DataFrame, merged_df: pd.DataFrame) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    known_entity_ids = set(entities_df["entity_id"])
    referenced_entity_ids = set(merged_df["entity_id"])
    orphaned = referenced_entity_ids - known_entity_ids
    if orphaned:
        preview = sorted(orphaned)[:5]
        issues.append(
            ValidationIssue(
                "entity_consistency",
                "error",
                f"Found {len(orphaned)} entity_id values referenced in events that do not exist in "
                f"entities.csv: {preview}{'...' if len(orphaned) > 5 else ''}",
            )
        )

    entity_type_map = entities_df.set_index("entity_id")["entity_type"].to_dict()
    known_mask = merged_df["entity_id"].isin(entity_type_map)
    mismatch_count = int((merged_df.loc[known_mask, "entity_type"] != merged_df.loc[known_mask, "entity_id"].map(entity_type_map)).sum())
    if mismatch_count > 0:
        issues.append(
            ValidationIssue(
                "entity_consistency",
                "error",
                f"Found {mismatch_count} events whose entity_type does not match the entity's actual type in entities.csv.",
            )
        )

    return issues


def run_all_validations(
    *,
    entities_df: pd.DataFrame,
    merged_df: pd.DataFrame,
    injected_event_count: int,
    start_date: date,
    end_date: date,
    max_attack_percentage: float,
) -> ValidationReport:
    issues: list[ValidationIssue] = []
    issues.extend(validate_attack_percentage(len(merged_df), injected_event_count, max_attack_percentage))
    issues.extend(validate_dataset_integrity(merged_df))
    issues.extend(validate_chronological_consistency(merged_df, start_date, end_date))
    issues.extend(validate_entity_consistency(entities_df, merged_df))
    return ValidationReport(issues=tuple(issues))