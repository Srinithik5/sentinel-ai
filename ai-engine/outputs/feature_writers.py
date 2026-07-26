from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from features.feature_registry import FEATURE_REGISTRY
from outputs.writers import write_csv, write_parquet
from validators.feature_validators import ValidationReport


def write_engineered_dataset(df: pd.DataFrame, csv_path: Path, parquet_path: Path) -> None:
    write_csv(df, csv_path)
    write_parquet(df, parquet_path)


def write_feature_dictionary(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    categories = sorted({feature.category for feature in FEATURE_REGISTRY})

    lines = [
        "# SentinelAI Feature Dictionary",
        "",
        f"{len(FEATURE_REGISTRY)} engineered features across {len(categories)} categories. Every feature is "
        f"computed from an entity's history strictly *before* the current event — none look at the current "
        f"event's own outcome or at ground truth.",
        "",
    ]

    for category in categories:
        lines.append(f"## {category.replace('_', ' ').title()}")
        lines.append("")
        lines.append("| Feature | Type | Description | Calculation | Purpose |")
        lines.append("|---|---|---|---|---|")
        for feature in FEATURE_REGISTRY:
            if feature.category != category:
                continue
            lines.append(
                f"| `{feature.name}` | {feature.dtype} | {feature.description} | {feature.calculation} | "
                f"{feature.purpose} |"
            )
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_feature_summary_report(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# SentinelAI Feature Engineering — Summary Report",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        f"Rows: {len(df):,}",
        f"Features: {len(FEATURE_REGISTRY)}",
        "",
        "## Per-Feature Statistics",
        "",
        "| Feature | Type | Mean / True-count | Std | Min | Max | Nulls |",
        "|---|---|---|---|---|---|---|",
    ]
    for feature in FEATURE_REGISTRY:
        if feature.name not in df.columns:
            continue
        series = df[feature.name]
        null_count = int(series.isna().sum())
        if feature.dtype in ("float", "int"):
            lines.append(
                f"| `{feature.name}` | {feature.dtype} | {series.mean():.3f} | {series.std():.3f} | "
                f"{series.min():.3f} | {series.max():.3f} | {null_count} |"
            )
        else:
            true_count = int(series.astype(bool).sum())
            lines.append(
                f"| `{feature.name}` | {feature.dtype} | {true_count:,} true ({true_count / len(df):.2%}) | "
                f"— | — | — | {null_count} |"
            )

    path.write_text("\n".join(lines), encoding="utf-8")


def write_validation_report(path: Path, report: ValidationReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# SentinelAI Feature Engineering — Validation Report",
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