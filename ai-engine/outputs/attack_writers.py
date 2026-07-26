from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from attacks.base import INJECTED_EVENT_COLUMNS, AttackInjectionResult, InjectedEvent
from outputs.writers import write_csv, write_parquet
from validators.injection_validators import ValidationReport

_SEVERITIES: tuple[str, ...] = ("low", "medium", "high", "critical")


def merge_events(events_df: pd.DataFrame, injected_events: list[InjectedEvent]) -> pd.DataFrame:
    """Combines the original (unmodified) events with newly injected attack
    events into one chronologically sorted table. Original rows keep their
    own `label` untouched; injected rows carry `label="attack"` plus full
    attack metadata. Original rows get null attack-metadata columns.
    """
    base = events_df.copy()
    # dataset_loader parses timestamp to datetime64 for internal date
    # arithmetic; InjectedEvent.to_row() emits an ISO string. Normalize both
    # sides to strings (matching Phase 2's own events.csv/parquet
    # convention) before concatenating, or the merged column ends up with
    # mixed Timestamp/str objects that PyArrow refuses to convert.
    base["timestamp"] = base["timestamp"].apply(lambda ts: ts.isoformat())
    for column in INJECTED_EVENT_COLUMNS:
        if column not in base.columns:
            base[column] = None
    base["injected"] = False

    injected_df = pd.DataFrame([event.to_row() for event in injected_events], columns=list(INJECTED_EVENT_COLUMNS))

    merged = pd.concat([base[list(INJECTED_EVENT_COLUMNS)], injected_df], ignore_index=True)
    sort_key = pd.to_datetime(merged["timestamp"], format="ISO8601")
    merged = merged.iloc[sort_key.argsort(kind="stable")].reset_index(drop=True)
    return merged


def write_injected_dataset(merged_df: pd.DataFrame, csv_path: Path, parquet_path: Path) -> None:
    write_csv(merged_df, csv_path)
    write_parquet(merged_df, parquet_path)


def write_attack_summary_report(
    path: Path,
    results: list[AttackInjectionResult],
    validation_report: ValidationReport,
    total_base_events: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    total_injected = sum(result.event_count for result in results)
    total_events = total_base_events + total_injected

    lines = [
        "# SentinelAI Attack Injection — Summary Report",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Overview",
        "",
        f"- Base dataset events: {total_base_events:,}",
        f"- Injected attack events: {total_injected:,}",
        f"- Total events after injection: {total_events:,}",
        f"- Injected share of dataset: {(total_injected / total_events) if total_events else 0:.2%}",
        "",
        "## Per-Attack Breakdown",
        "",
        "| Attack Type | Incidents | Events |",
        "|---|---|---|",
    ]
    for result in results:
        lines.append(f"| {result.attack_type} | {result.incident_count} | {result.event_count} |")

    lines.extend(
        [
            "",
            "## Validation",
            "",
            f"- Status: {'PASSED' if validation_report.passed else 'FAILED'}",
            f"- Errors: {validation_report.error_count}",
            f"- Warnings: {validation_report.warning_count}",
        ]
    )
    if validation_report.issues:
        lines.extend(["", "| Check | Severity | Message |", "|---|---|---|"])
        for issue in validation_report.issues:
            lines.append(f"| {issue.check} | {issue.severity} | {issue.message} |")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_injection_statistics(path: Path, results: list[AttackInjectionResult], merged_df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for result in results:
        attack_events = merged_df[merged_df["attack_type"] == result.attack_type]
        severity_counts = attack_events["severity"].value_counts().to_dict()
        row: dict[str, object] = {
            "attack_type": result.attack_type,
            "incident_count": result.incident_count,
            "event_count": result.event_count,
            "targeted_entities": len(set(result.targeted_entity_ids)),
            "mean_confidence": round(float(attack_events["confidence"].mean()), 3) if not attack_events.empty else None,
        }
        for severity in _SEVERITIES:
            row[f"severity_{severity}_count"] = int(severity_counts.get(severity, 0))
        rows.append(row)

    write_csv(pd.DataFrame(rows), path)