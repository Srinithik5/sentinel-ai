from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from profiles.profile_manager import BehaviourProfile, WarmupStrategy
from validators.profile_validators import ValidationReport


def write_behaviour_profiles(profiles: list[BehaviourProfile], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [profile.to_dict() for profile in profiles]
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def write_profile_summary(profiles: list[BehaviourProfile], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "entity_id": profile.entity_id,
            "entity_type": profile.entity_type,
            "version": profile.version,
            "sample_count": profile.statistical.sample_count,
            "avg_login_hour": profile.statistical.avg_login_hour,
            "avg_session_duration": profile.statistical.avg_session_duration,
            "failure_rate": profile.statistical.failure_rate,
            "working_hour_ratio": profile.statistical.working_hour_ratio,
            "department": profile.relationship.department,
            "resource_sharing_score": profile.relationship.resource_sharing_score,
            "drift_score": profile.drift.drift_score,
            "is_significant_drift": profile.drift.is_significant_drift,
            "history_length": profile.cold_start.history_length,
            "confidence_score": profile.cold_start.confidence_score,
            "warmup_strategy": profile.cold_start.warmup_strategy.value,
        }
        for profile in profiles
    ]
    pd.DataFrame(rows).to_csv(path, index=False)


def write_drift_report(profiles: list[BehaviourProfile], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    significant = [profile for profile in profiles if profile.drift.is_significant_drift]
    drift_scores = [profile.drift.drift_score for profile in profiles]

    lines = [
        "# SentinelAI Behaviour Profiling — Drift Report",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        f"Profiles evaluated: {len(profiles)}",
        f"Profiles with significant drift: {len(significant)}",
    ]
    if drift_scores:
        lines.append(f"Mean drift score: {sum(drift_scores) / len(drift_scores):.4f}")
        lines.append(f"Max drift score: {max(drift_scores):.4f}")
    lines.append("")

    if significant:
        lines.extend(
            [
                "## Entities With Significant Drift",
                "",
                "| Entity | Version | Drift Score | Drifted Dimensions | Historical N | Current N |",
                "|---|---|---|---|---|---|",
            ]
        )
        for profile in sorted(significant, key=lambda p: -p.drift.drift_score):
            dims = ", ".join(profile.drift.drifted_dimensions) or "—"
            lines.append(
                f"| {profile.entity_id} | {profile.version} | {profile.drift.drift_score:.4f} | {dims} | "
                f"{profile.drift.historical_sample_count} | {profile.drift.current_sample_count} |"
            )
    else:
        lines.append("No entities exceeded the drift significance threshold in this run.")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_cold_start_report(profiles: list[BehaviourProfile], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    by_strategy: dict[WarmupStrategy, list[BehaviourProfile]] = {strategy: [] for strategy in WarmupStrategy}
    for profile in profiles:
        by_strategy[profile.cold_start.warmup_strategy].append(profile)

    lines = [
        "# SentinelAI Behaviour Profiling — Cold Start Report",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        f"Total profiles: {len(profiles)}",
        "",
        "## Warm-Up Distribution",
        "",
        "| Strategy | Count | Percentage |",
        "|---|---|---|",
    ]
    for strategy in WarmupStrategy:
        count = len(by_strategy[strategy])
        percentage = (count / len(profiles)) if profiles else 0.0
        lines.append(f"| {strategy.value} | {count} | {percentage:.2%} |")

    insufficient = by_strategy[WarmupStrategy.INSUFFICIENT_DATA]
    if insufficient:
        lines.extend(
            ["", "## Entities With Insufficient Data", "", "| Entity | History Length | Confidence |", "|---|---|---|"]
        )
        for profile in sorted(insufficient, key=lambda p: p.entity_id):
            lines.append(
                f"| {profile.entity_id} | {profile.cold_start.history_length} | "
                f"{profile.cold_start.confidence_score:.4f} |"
            )

    path.write_text("\n".join(lines), encoding="utf-8")


def write_validation_report(report: ValidationReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# SentinelAI Behaviour Profiling — Validation Report",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        f"Status: {'PASSED' if report.passed else 'FAILED'}",
        f"Errors: {report.error_count}",
        f"Warnings: {report.warning_count}",
        "",
    ]
    if report.issues:
        lines.extend(["| Check | Severity | Message |", "|---|---|---|"])
        for issue in report.issues:
            lines.append(f"| {issue.check} | {issue.severity} | {issue.message} |")
    else:
        lines.append("No issues found.")

    path.write_text("\n".join(lines), encoding="utf-8")