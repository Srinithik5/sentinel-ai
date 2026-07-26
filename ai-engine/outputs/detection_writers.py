from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

from detection.decision_engine import DetectionVerdict
from detection.detection_engine import DetectionResult
from detection.threshold_manager import SeverityLevel
from outputs.writers import write_csv, write_parquet
from validators.detection_validators import ValidationReport

_PERCENTILES: tuple[float, ...] = (0.5, 0.75, 0.90, 0.95, 0.99)


def write_detection_results(results: list[DetectionResult], csv_path: Path, parquet_path: Path) -> None:
    df = pd.DataFrame([result.to_dict() for result in results])
    write_csv(df, csv_path)
    write_parquet(df, parquet_path)


def write_risk_score_report(results: list[DetectionResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    risk_scores = pd.Series([result.risk_assessment.risk_score for result in results], dtype=float)
    severity_counts = Counter(result.severity for result in results)

    lines = [
        "# SentinelAI Phase 4 — Risk Score Report",
        "",
        f"Total events scored: {len(results):,}",
        "",
        "## Risk Score Distribution",
        "",
        f"- Mean: {risk_scores.mean():.2f}",
        f"- Std dev: {risk_scores.std():.2f}",
        f"- Min: {risk_scores.min():.2f}",
        f"- Max: {risk_scores.max():.2f}",
    ]
    for pct in _PERCENTILES:
        lines.append(f"- p{int(pct * 100)}: {risk_scores.quantile(pct):.2f}")

    lines.append("")
    lines.append("## Severity Breakdown")
    lines.append("")
    lines.append("| Severity | Count | Percentage |")
    lines.append("|---|---|---|")
    for severity in SeverityLevel:
        count = severity_counts.get(severity, 0)
        pct = (count / len(results) * 100) if results else 0.0
        lines.append(f"| {severity.value} | {count:,} | {pct:.2f}% |")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_detection_summary(results: list[DetectionResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    verdict_counts = Counter(result.verdict for result in results)

    entity_type_breakdown: dict[str, Counter] = {}
    for result in results:
        entity_type = result.entity_type or "unknown"
        entity_type_breakdown.setdefault(entity_type, Counter())[result.verdict] += 1

    lines = [
        "# SentinelAI Phase 4 — Detection Summary",
        "",
        f"Total events processed: {len(results):,}",
        "",
        "## Verdict Breakdown",
        "",
        "| Verdict | Count | Percentage |",
        "|---|---|---|",
    ]
    for verdict in DetectionVerdict:
        count = verdict_counts.get(verdict, 0)
        pct = (count / len(results) * 100) if results else 0.0
        lines.append(f"| {verdict.value} | {count:,} | {pct:.2f}% |")

    lines.append("")
    lines.append("## Verdict Breakdown by Entity Type")
    lines.append("")
    lines.append("| Entity Type | Normal | Suspicious | Anomalous |")
    lines.append("|---|---|---|---|")
    for entity_type, counts in sorted(entity_type_breakdown.items()):
        lines.append(
            f"| {entity_type} | {counts.get(DetectionVerdict.NORMAL, 0):,} "
            f"| {counts.get(DetectionVerdict.SUSPICIOUS, 0):,} | {counts.get(DetectionVerdict.ANOMALOUS, 0):,} |"
        )

    path.write_text("\n".join(lines), encoding="utf-8")


def write_detection_metrics(results: list[DetectionResult], path: Path) -> None:
    """Retrospective quality metrics ONLY. Ground truth (`is_attack`) is
    never read by any detection component — it is attached to results
    after detection completes (see `run_detection`) and used here purely
    to measure how well `verdict != NORMAL` lines up with known attacks.
    This is evaluation, not classification: the engine never learns or
    reports which attack type an event resembles.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    labeled = [result for result in results if result.is_attack is not None]

    lines = [
        "# SentinelAI Phase 4 — Detection Metrics",
        "",
        "Ground truth is used here only for retrospective evaluation of detection quality. "
        "It is never fed into the detection engine itself — see `detection_engine.run_detection`, "
        "which attaches `is_attack` to each result only after the verdict has already been decided.",
        "",
    ]

    if not labeled:
        lines.append("No ground-truth labels (`is_attack`) were present in the input — metrics unavailable.")
        path.write_text("\n".join(lines), encoding="utf-8")
        return

    true_positive = sum(1 for r in labeled if r.is_attack and r.verdict != DetectionVerdict.NORMAL)
    false_positive = sum(1 for r in labeled if not r.is_attack and r.verdict != DetectionVerdict.NORMAL)
    true_negative = sum(1 for r in labeled if not r.is_attack and r.verdict == DetectionVerdict.NORMAL)
    false_negative = sum(1 for r in labeled if r.is_attack and r.verdict == DetectionVerdict.NORMAL)

    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = (true_positive + true_negative) / len(labeled) if labeled else 0.0

    lines.extend(
        [
            "## Confusion Matrix (flagged = verdict != normal)",
            "",
            "| | Predicted Attack | Predicted Normal |",
            "|---|---|---|",
            f"| Actual Attack | {true_positive:,} (TP) | {false_negative:,} (FN) |",
            f"| Actual Normal | {false_positive:,} (FP) | {true_negative:,} (TN) |",
            "",
            "## Retrospective Quality Metrics",
            "",
            f"- Precision: {precision:.4f}",
            f"- Recall: {recall:.4f}",
            f"- F1 score: {f1:.4f}",
            f"- Accuracy: {accuracy:.4f}",
            f"- Labeled events evaluated: {len(labeled):,} of {len(results):,} total",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def write_validation_report(report: ValidationReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# SentinelAI Phase 4 — Validation Report",
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