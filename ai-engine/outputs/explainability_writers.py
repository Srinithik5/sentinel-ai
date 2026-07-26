from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

from explainability.explainability_engine import ExplainabilityResult
from explainability.explainability_validator import ValidationReport
from outputs.writers import write_csv, write_parquet

_TOP_SUMMARY_COUNT = 25


def write_explainability_report(results: list[ExplainabilityResult], csv_path: Path, parquet_path: Path) -> None:
    df = pd.DataFrame([result.to_dict() for result in results])
    write_csv(df, csv_path)
    write_parquet(df, parquet_path)


def write_feature_attribution_report(results: list[ExplainabilityResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    contribution_by_dimension: dict[str, list[float]] = {}
    top_dimension_counts: Counter[str] = Counter()
    for result in results:
        if not result.contributions:
            continue
        top_dimension_counts[result.contributions[0].dimension] += 1
        for contribution in result.contributions:
            contribution_by_dimension.setdefault(contribution.dimension, []).append(contribution.contribution_percentage)

    lines = [
        "# SentinelAI Phase 6 — Feature Attribution Report",
        "",
        f"Total explained events: {len(results):,}",
        "",
        "## Average Contribution by Dimension",
        "",
        "| Dimension | Avg Contribution % | Min | Max | Times #1 Contributor | % of Events |",
        "|---|---|---|---|---|---|",
    ]
    for dimension in sorted(contribution_by_dimension, key=lambda d: sum(contribution_by_dimension[d]) / len(contribution_by_dimension[d]), reverse=True):
        values = pd.Series(contribution_by_dimension[dimension], dtype=float)
        top_count = top_dimension_counts.get(dimension, 0)
        top_pct = (top_count / len(results) * 100) if results else 0.0
        lines.append(
            f"| {dimension} | {values.mean():.2f}% | {values.min():.2f}% | {values.max():.2f}% | {top_count:,} | {top_pct:.2f}% |"
        )

    path.write_text("\n".join(lines), encoding="utf-8")


def write_recommendation_report(results: list[ExplainabilityResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    action_counts: Counter[str] = Counter()
    priority_counts: Counter[str] = Counter()
    action_by_attack_type: dict[str, Counter[str]] = {}
    for result in results:
        attack_type = result.evidence.classification.attack_type
        for action in result.recommendations:
            action_counts[action.action] += 1
            priority_counts[action.priority] += 1
            action_by_attack_type.setdefault(attack_type, Counter())[action.action] += 1

    lines = [
        "# SentinelAI Phase 6 — Recommendation Report",
        "",
        f"Total explained events: {len(results):,}",
        "",
        "## Priority Breakdown",
        "",
        "| Priority | Count |",
        "|---|---|",
    ]
    for priority in ("immediate", "high", "standard"):
        lines.append(f"| {priority} | {priority_counts.get(priority, 0):,} |")

    lines.append("")
    lines.append("## Most Common Recommended Actions")
    lines.append("")
    lines.append("| Action | Count |")
    lines.append("|---|---|")
    for action, count in action_counts.most_common():
        lines.append(f"| {action} | {count:,} |")

    lines.append("")
    lines.append("## Recommended Actions by Attack Type")
    lines.append("")
    for attack_type in sorted(action_by_attack_type):
        lines.append(f"### {attack_type}")
        lines.append("")
        lines.append("| Action | Count |")
        lines.append("|---|---|")
        for action, count in action_by_attack_type[attack_type].most_common():
            lines.append(f"| {action} | {count:,} |")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_analyst_summary(
    results: list[ExplainabilityResult],
    csv_path: Path,
    parquet_path: Path,
    markdown_path: Path,
) -> None:
    df = pd.DataFrame([result.summary.to_dict() for result in results])
    write_csv(df, csv_path)
    write_parquet(df, parquet_path)

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    severity_counts = Counter(result.evidence.detection.severity for result in results)
    attack_type_counts = Counter(result.evidence.classification.attack_type for result in results)
    confidence_level_counts = Counter(result.confidence_explanation.level.value for result in results)

    lines = [
        "# SentinelAI Phase 6 — Analyst Summary",
        "",
        f"Total explained events: {len(results):,}",
        "",
        "## Severity Breakdown",
        "",
        "| Severity | Count |",
        "|---|---|",
    ]
    for severity, count in sorted(severity_counts.items(), key=lambda item: item[0]):
        lines.append(f"| {severity} | {count:,} |")

    lines.append("")
    lines.append("## Attack Type Breakdown")
    lines.append("")
    lines.append("| Attack Type | Count |")
    lines.append("|---|---|")
    for attack_type, count in attack_type_counts.most_common():
        lines.append(f"| {attack_type} | {count:,} |")

    lines.append("")
    lines.append("## Confidence Level Breakdown")
    lines.append("")
    lines.append("| Confidence Level | Count |")
    lines.append("|---|---|")
    for level, count in sorted(confidence_level_counts.items()):
        lines.append(f"| {level} | {count:,} |")

    ranked = sorted(results, key=lambda r: r.evidence.detection.risk_score, reverse=True)
    top_results = ranked[:_TOP_SUMMARY_COUNT]

    lines.append("")
    lines.append(f"## Top {len(top_results)} Highest-Risk Events (full detail)")
    lines.append("")
    lines.append(f"The complete, structured summary for all {len(results):,} events is in `analyst_summary.csv` / `analyst_summary.parquet`. The highest-risk events are expanded below for direct review.")
    lines.append("")
    for result in top_results:
        lines.append("```")
        lines.append(result.summary.to_text())
        lines.append("```")
        lines.append("")

    markdown_path.write_text("\n".join(lines), encoding="utf-8")


def write_explainability_validation_report(report: ValidationReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# SentinelAI Phase 6 — Validation Report",
        "",
        f"Result: {'PASSED' if report.passed else 'FAILED'}",
        f"Errors: {report.error_count}",
        f"Warnings: {report.warning_count}",
        "",
    ]
    if not report.issues:
        lines.append("No issues found.")
    else:
        lines.append("| Check | Severity | Message |")
        lines.append("|---|---|---|")
        for issue in report.issues[:500]:
            lines.append(f"| {issue.check} | {issue.severity} | {issue.message} |")
        if len(report.issues) > 500:
            lines.append(f"\n...and {len(report.issues) - 500:,} more issue(s) truncated for report length.")

    path.write_text("\n".join(lines), encoding="utf-8")