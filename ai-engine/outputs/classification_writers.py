from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

from classification.attack_registry import ATTACK_REGISTRY, AttackType
from classification.classification_engine import ClassificationResult
from classification.classification_validator import ValidationReport
from outputs.writers import write_csv, write_parquet

_PERCENTILES: tuple[float, ...] = (0.5, 0.75, 0.90, 0.95, 0.99)
_HISTOGRAM_BUCKETS: tuple[tuple[float, float], ...] = (
    (0.0, 0.2),
    (0.2, 0.4),
    (0.4, 0.6),
    (0.6, 0.8),
    (0.8, 1.01),
)


def write_classification_report(results: list[ClassificationResult], csv_path: Path, parquet_path: Path) -> None:
    df = pd.DataFrame([result.to_dict() for result in results])
    write_csv(df, csv_path)
    write_parquet(df, parquet_path)


def write_attack_summary(results: list[ClassificationResult], path: Path) -> None:
    """Summarizes what was classified: counts and average confidence per
    attack type, severity breakdown, MITRE tactic breakdown, and — only
    when Phase 2B ground truth happens to be present in the input — a
    retrospective, evaluation-only agreement rate against it. Ground truth
    is never read anywhere upstream of this report; it is only compared
    against the classifier's own already-decided output, exactly like
    Phase 4's detection_metrics discipline.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    attack_type_counts = Counter(result.attack_type for result in results)
    severity_counts = Counter(result.severity for result in results)

    confidence_by_type: dict[AttackType, list[float]] = {}
    for result in results:
        confidence_by_type.setdefault(result.attack_type, []).append(result.confidence)

    lines = [
        "# SentinelAI Phase 5 — Attack Summary",
        "",
        f"Total classified events: {len(results):,}",
        "",
        "## Attack Type Breakdown",
        "",
        "| Attack Type | MITRE Tactic | MITRE Technique | Count | Percentage | Avg Confidence |",
        "|---|---|---|---|---|---|",
    ]
    for attack_type, definition in ATTACK_REGISTRY.items():
        count = attack_type_counts.get(attack_type, 0)
        if count == 0:
            continue
        pct = count / len(results) * 100 if results else 0.0
        avg_confidence = sum(confidence_by_type[attack_type]) / count
        lines.append(
            f"| {definition.display_name} | {definition.mitre_tactic} | {definition.mitre_technique} "
            f"| {count:,} | {pct:.2f}% | {avg_confidence:.4f} |"
        )

    lines.append("")
    lines.append("## Severity Breakdown")
    lines.append("")
    lines.append("| Severity | Count | Percentage |")
    lines.append("|---|---|---|")
    for severity, count in sorted(severity_counts.items(), key=lambda item: item[0].value):
        pct = count / len(results) * 100 if results else 0.0
        lines.append(f"| {severity.value} | {count:,} | {pct:.2f}% |")

    labeled = [result for result in results if result.ground_truth_attack_type is not None]
    lines.append("")
    lines.append("## Evaluation vs Ground Truth (retrospective only — never a classification input)")
    lines.append("")
    if not labeled:
        lines.append("No ground-truth `attack_type` labels were present in the input — evaluation unavailable.")
    else:
        correct = sum(1 for result in labeled if result.attack_type.value == result.ground_truth_attack_type)
        agreement_rate = correct / len(labeled)
        lines.append(f"- Labeled events evaluated: {len(labeled):,} of {len(results):,} total")
        lines.append(f"- Overall agreement rate: {agreement_rate:.4f} ({correct:,} of {len(labeled):,})")
        lines.append("")
        lines.append("| Ground Truth Attack Type | Classified Correctly | Total | Agreement Rate |")
        lines.append("|---|---|---|---|")
        by_ground_truth: dict[str, list[ClassificationResult]] = {}
        for result in labeled:
            by_ground_truth.setdefault(result.ground_truth_attack_type, []).append(result)
        for ground_truth_type in sorted(by_ground_truth):
            group = by_ground_truth[ground_truth_type]
            group_correct = sum(1 for result in group if result.attack_type.value == ground_truth_type)
            lines.append(f"| {ground_truth_type} | {group_correct:,} | {len(group):,} | {group_correct / len(group):.4f} |")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_confidence_distribution(results: list[ClassificationResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    confidences = pd.Series([result.confidence for result in results], dtype=float)

    lines = [
        "# SentinelAI Phase 5 — Confidence Distribution",
        "",
        f"Total classified events: {len(results):,}",
        "",
        "## Overall Distribution",
        "",
    ]

    if results:
        lines.extend(
            [
                f"- Mean: {confidences.mean():.4f}",
                f"- Std dev: {confidences.std():.4f}",
                f"- Min: {confidences.min():.4f}",
                f"- Max: {confidences.max():.4f}",
            ]
        )
        for pct in _PERCENTILES:
            lines.append(f"- p{int(pct * 100)}: {confidences.quantile(pct):.4f}")

        lines.append("")
        lines.append("## Confidence Histogram")
        lines.append("")
        lines.append("| Range | Count | Bar |")
        lines.append("|---|---|---|")
        for low, high in _HISTOGRAM_BUCKETS:
            count = int(((confidences >= low) & (confidences < high)).sum())
            bar = "#" * max(1, round(count / max(len(results), 1) * 40)) if count else ""
            lines.append(f"| [{low:.1f}, {min(high, 1.0):.1f}) | {count:,} | {bar} |")

        lines.append("")
        lines.append("## Average Confidence by Attack Type")
        lines.append("")
        lines.append("| Attack Type | Count | Avg Confidence | Min | Max |")
        lines.append("|---|---|---|---|---|")
        by_type: dict[AttackType, list[float]] = {}
        for result in results:
            by_type.setdefault(result.attack_type, []).append(result.confidence)
        for attack_type in AttackType:
            values = by_type.get(attack_type)
            if not values:
                continue
            series = pd.Series(values, dtype=float)
            lines.append(
                f"| {attack_type.value} | {len(values):,} | {series.mean():.4f} | {series.min():.4f} | {series.max():.4f} |"
            )
    else:
        lines.append("No classified events to summarize.")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_classification_validation_report(report: ValidationReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# SentinelAI Phase 5 — Validation Report",
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