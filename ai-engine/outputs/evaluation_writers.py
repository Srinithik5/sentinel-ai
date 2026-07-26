from __future__ import annotations

from pathlib import Path

import pandas as pd

from evaluation.report_generator import EvaluationBundle
from outputs.writers import write_csv


def _write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_evaluation_report(bundle: EvaluationBundle, path: Path) -> None:
    """The top-level Evaluation Report — a judging-criteria-oriented
    executive summary of the whole run."""
    d, c = bundle.detection, bundle.classification
    lines = [
        "# SentinelAI Phase 8 — Evaluation Report",
        "",
        f"Run ID: {bundle.run_id}",
        f"Generated: {bundle.generated_at}",
        f"Validation: {'PASSED' if bundle.validation.passed else 'FAILED'} "
        f"({bundle.validation.error_count} errors, {bundle.validation.warning_count} warnings)",
        "",
        "## Detection Performance",
        "",
        f"- Precision: {d.confusion.precision:.4f}",
        f"- Recall: {d.confusion.recall:.4f}",
        f"- F1 Score: {d.confusion.f1:.4f}",
        f"- ROC-AUC: {d.roc.auc:.4f}",
        f"- PR-AUC: {d.pr.auc:.4f}",
        f"- False Positive Rate: {d.false_positive_rate:.4f}",
        f"- False Negative Rate: {d.false_negative_rate:.4f}",
        f"- Top-{d.top_percentile:g}% Analyst Alert Precision: {d.top_percentile_precision:.4f} (n={d.top_percentile_count:,})",
        f"- Evaluated on {d.labeled_count:,} labeled events (of {d.sample_count:,} total).",
        "",
        "## Classification Performance",
        "",
        f"- Macro F1: {c.macro_f1:.4f}",
        f"- Weighted F1: {c.weighted_f1:.4f}",
        f"- Overall Accuracy: {c.overall_accuracy:.4f}",
        f"- Evaluated on {c.labeled_count:,} labeled events across {len(c.classes)} classes.",
        "",
        "## Cold Start Snapshot",
        "",
        "| Segment | Events | Avg Risk | Flagged Rate | FP Rate |",
        "|---|---|---|---|---|",
    ]
    for segment in bundle.cold_start.segments:
        fp = f"{segment.false_positive_rate:.4f}" if segment.false_positive_rate is not None else "n/a"
        lines.append(f"| {segment.segment_name} | {segment.event_count:,} | {segment.avg_risk_score:.2f} | {segment.flagged_rate:.4f} | {fp} |")

    lines.extend(
        [
            "",
            "## Concept Drift Snapshot",
            "",
            f"- Weekly periods observed: {len(bundle.concept_drift.weekly_drift)}",
            f"- Monthly periods observed: {len(bundle.concept_drift.monthly_drift)}",
            f"- Entities with more than one profile version: {bundle.concept_drift.profile_updates.entities_with_multiple_versions:,} of {bundle.concept_drift.profile_updates.total_entities:,}",
            f"- Detection stability (avg risk-score std dev on normal events): {bundle.concept_drift.detection_stability.avg_risk_score_std:.4f}",
            "",
            "## Performance Snapshot",
            "",
            f"- Streaming throughput: {bundle.streaming.events_per_second:,.1f} events/sec",
            f"- Streaming avg latency: {bundle.streaming.avg_latency_ms:.4f} ms/event",
            f"- Largest scalability tier tested: {bundle.scalability.tiers[-1].target_entity_count:,} entities at {bundle.scalability.tiers[-1].throughput_events_per_sec:,.1f} events/sec",
            "",
            "See `metrics_report.md`, `scalability_report.md`, `cold_start_report.md`, `concept_drift_report.md`, and `benchmark_summary.md` for full detail.",
        ]
    )
    _write_markdown(path, lines)


def write_metrics_report(bundle: EvaluationBundle, path: Path) -> None:
    """Detailed Detection + Classification metrics: full confusion
    matrices, per-class breakdowns, and curve summaries."""
    d, c = bundle.detection, bundle.classification
    lines = [
        "# SentinelAI Phase 8 — Metrics Report",
        "",
        "## Detection Evaluation",
        "",
        "### Confusion Matrix",
        "",
        "| | Predicted Anomalous | Predicted Normal |",
        "|---|---|---|",
        f"| Actual Attack | {d.confusion.true_positive:,} (TP) | {d.confusion.false_negative:,} (FN) |",
        f"| Actual Normal | {d.confusion.false_positive:,} (FP) | {d.confusion.true_negative:,} (TN) |",
        "",
        "### Metrics",
        "",
        f"- Precision: {d.confusion.precision:.4f}",
        f"- Recall: {d.confusion.recall:.4f}",
        f"- F1 Score: {d.confusion.f1:.4f}",
        f"- ROC-AUC: {d.roc.auc:.4f}",
        f"- PR-AUC: {d.pr.auc:.4f}",
        f"- False Positive Rate: {d.false_positive_rate:.4f}",
        f"- False Negative Rate: {d.false_negative_rate:.4f}",
        f"- Top-{d.top_percentile:g}% Analyst Alert Precision: {d.top_percentile_precision:.4f} (n={d.top_percentile_count:,})",
        "",
        "Full ROC/PR curve points are in `detection_roc_curve.csv` / `detection_pr_curve.csv` alongside this report.",
        "",
        "## Classification Evaluation",
        "",
        "### Confusion Matrix (rows = actual, columns = predicted)",
        "",
    ]
    header = "| Actual \\ Predicted | " + " | ".join(c.classes) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (len(c.classes) + 1))
    for actual in c.classes:
        row = [str(c.confusion_matrix[actual][predicted]) for predicted in c.classes]
        lines.append(f"| {actual} | " + " | ".join(row) + " |")

    lines.extend(
        [
            "",
            "### Per-Class Metrics",
            "",
            "| Class | Support | Precision | Recall | F1 |",
            "|---|---|---|---|---|",
        ]
    )
    for item in c.per_class:
        lines.append(f"| {item.class_name} | {item.support:,} | {item.precision:.4f} | {item.recall:.4f} | {item.f1:.4f} |")

    lines.extend(
        [
            "",
            f"- Macro F1: {c.macro_f1:.4f}",
            f"- Weighted F1: {c.weighted_f1:.4f}",
            f"- Overall Accuracy: {c.overall_accuracy:.4f}",
        ]
    )
    _write_markdown(path, lines)

    csv_dir = path.parent
    roc_df = pd.DataFrame([point.to_dict() for point in d.roc.points])
    pr_df = pd.DataFrame([point.to_dict() for point in d.pr.points])
    write_csv(roc_df, csv_dir / "detection_roc_curve.csv")
    write_csv(pr_df, csv_dir / "detection_pr_curve.csv")

    confusion_rows = [{"actual": actual, **{f"predicted_{p}": count for p, count in row.items()}} for actual, row in c.confusion_matrix.items()]
    write_csv(pd.DataFrame(confusion_rows), csv_dir / "classification_confusion_matrix.csv")


def write_scalability_report(bundle: EvaluationBundle, path: Path) -> None:
    s = bundle.scalability
    lines = [
        "# SentinelAI Phase 8 — Scalability Report",
        "",
        s.methodology_note,
        "",
        f"Events replayed per entity: {s.events_per_entity}",
        "",
        "| Target Entities | Real | Synthetic | Events | Total (s) | Avg Latency (ms) | Peak Memory (MB) | CPU (s) | Throughput (events/sec) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for tier in s.tiers:
        lines.append(
            f"| {tier.target_entity_count:,} | {tier.real_entity_count:,} | {tier.synthetic_entity_count:,} | "
            f"{tier.event_count:,} | {tier.total_seconds:.4f} | {tier.avg_latency_ms:.4f} | {tier.peak_memory_mb:.3f} | "
            f"{tier.cpu_seconds:.4f} | {tier.throughput_events_per_sec:,.1f} |"
        )
    _write_markdown(path, lines)

    tiers_df = pd.DataFrame([tier.to_dict() for tier in s.tiers])
    write_csv(tiers_df, path.parent / "scalability_tiers.csv")


def write_cold_start_report(bundle: EvaluationBundle, path: Path) -> None:
    cs = bundle.cold_start
    lines = [
        "# SentinelAI Phase 8 — Cold Start Report",
        "",
        "## Population Segments",
        "",
        "| Segment | Events | Avg Risk | Avg Anomaly Score | Flagged Rate | False Positive Rate |",
        "|---|---|---|---|---|---|",
    ]
    for segment in cs.segments:
        fp = f"{segment.false_positive_rate:.4f}" if segment.false_positive_rate is not None else "n/a"
        lines.append(
            f"| {segment.segment_name} | {segment.event_count:,} | {segment.avg_risk_score:.2f} | "
            f"{segment.avg_anomaly_score:.4f} | {segment.flagged_rate:.4f} | {fp} |"
        )

    lines.extend(
        [
            "",
            "## Warm-Up Curve (risk score / confidence vs. history length)",
            "",
            "| History Length | Events | Avg Risk Score | Avg Historical Confidence |",
            "|---|---|---|---|",
        ]
    )
    for bucket in cs.warmup_curve:
        lines.append(f"| {bucket.history_length_range} | {bucket.event_count:,} | {bucket.avg_risk_score:.2f} | {bucket.avg_historical_confidence:.4f} |")

    lines.extend(
        [
            "",
            "## Confidence Calibration Curve",
            "",
            "Within events whose historical_confidence fell in each range, how often did the detection verdict "
            "actually agree with ground truth? A well-calibrated detector's empirical accuracy should track its "
            "own confidence.",
            "",
            "| Confidence Range | Events | Avg Confidence | Empirical Accuracy |",
            "|---|---|---|---|",
        ]
    )
    for calibration_bin in cs.calibration_curve:
        accuracy = f"{calibration_bin.empirical_accuracy:.4f}" if calibration_bin.empirical_accuracy is not None else "n/a (no labeled events in bin)"
        lines.append(f"| {calibration_bin.confidence_range} | {calibration_bin.event_count:,} | {calibration_bin.avg_confidence:.4f} | {accuracy} |")

    _write_markdown(path, lines)


def write_concept_drift_report(bundle: EvaluationBundle, path: Path) -> None:
    cd = bundle.concept_drift
    lines = [
        "# SentinelAI Phase 8 — Concept Drift Report",
        "",
        "## Weekly Drift",
        "",
        "| Week | Events | Avg Drift Score | p90 Drift Score |",
        "|---|---|---|---|",
    ]
    for period in cd.weekly_drift:
        lines.append(f"| {period.period_label} | {period.event_count:,} | {period.avg_drift_score:.4f} | {period.p90_drift_score:.4f} |")

    lines.extend(
        [
            "",
            "## Monthly Drift",
            "",
            "| Month | Events | Avg Drift Score | p90 Drift Score |",
            "|---|---|---|---|",
        ]
    )
    for period in cd.monthly_drift:
        lines.append(f"| {period.period_label} | {period.event_count:,} | {period.avg_drift_score:.4f} | {period.p90_drift_score:.4f} |")

    pu = cd.profile_updates
    lines.extend(
        [
            "",
            "## Adaptive Profile Updates",
            "",
            f"- Total profiled entities: {pu.total_entities:,}",
            f"- Entities with more than one stored profile version: {pu.entities_with_multiple_versions:,}",
            f"- Average drift score at latest version: {pu.avg_latest_drift_score:.4f}",
            f"- Maximum drift score observed at latest version: {pu.max_latest_drift_score:.4f}",
            "",
            pu.note,
            "",
            "## Detection Stability",
            "",
            f"- Entities evaluated (>=5 normal-verdict events): {cd.detection_stability.entities_evaluated:,}",
            f"- Average risk-score std dev on normal events: {cd.detection_stability.avg_risk_score_std:.4f}",
            f"- Median risk-score std dev on normal events: {cd.detection_stability.median_risk_score_std:.4f}",
            f"- p90 risk-score std dev on normal events: {cd.detection_stability.p90_risk_score_std:.4f}",
        ]
    )
    _write_markdown(path, lines)

    weekly_df = pd.DataFrame([period.to_dict() for period in cd.weekly_drift])
    monthly_df = pd.DataFrame([period.to_dict() for period in cd.monthly_drift])
    write_csv(weekly_df, path.parent / "concept_drift_weekly.csv")
    write_csv(monthly_df, path.parent / "concept_drift_monthly.csv")


def write_benchmark_summary(bundle: EvaluationBundle, path: Path) -> None:
    st, dl, sc = bundle.streaming, bundle.dashboard_latency, bundle.scalability
    lines = [
        "# SentinelAI Phase 8 — Benchmark Summary",
        "",
        "## Streaming Benchmark",
        "",
        f"- Events processed: {st.event_count:,}",
        f"- Total time: {st.total_seconds:.4f}s",
        f"- Throughput: {st.events_per_second:,.1f} events/sec",
        f"- Average latency: {st.avg_latency_ms:.4f} ms",
        f"- p50 latency: {st.p50_latency_ms:.4f} ms",
        f"- p95 latency: {st.p95_latency_ms:.4f} ms",
        f"- p99 latency: {st.p99_latency_ms:.4f} ms",
        f"- Worst latency: {st.worst_latency_ms:.4f} ms",
        "",
        "## Scalability Benchmark (see scalability_report.md for full detail)",
        "",
        "| Target Entities | Throughput (events/sec) | Avg Latency (ms) | Peak Memory (MB) |",
        "|---|---|---|---|",
    ]
    for tier in sc.tiers:
        lines.append(f"| {tier.target_entity_count:,} | {tier.throughput_events_per_sec:,.1f} | {tier.avg_latency_ms:.4f} | {tier.peak_memory_mb:.3f} |")

    lines.extend(
        [
            "",
            "## Dashboard Benchmark",
            "",
            "### API (Data Load) Latency",
            "",
            "| Fixture | Payload (bytes) | Read (s) | Parse (s) |",
            "|---|---|---|---|",
        ]
    )
    for entry in dl.api_latency:
        lines.append(f"| {entry.fixture_name} | {entry.payload_bytes:,} | {entry.read_seconds:.6f} | {entry.parse_seconds:.6f} |")

    lines.extend(
        [
            "",
            "### Search Latency",
            "",
            f"- Queries run: {dl.search_latency.query_count}",
            f"- Dataset size: {dl.search_latency.dataset_size:,} alerts",
            f"- Average latency: {dl.search_latency.avg_latency_ms:.4f} ms",
            f"- p95 latency: {dl.search_latency.p95_latency_ms:.4f} ms",
            f"- Worst latency: {dl.search_latency.worst_latency_ms:.4f} ms",
            "",
            "### Rendering Proxy",
            "",
            f"- Payload size: {dl.render_proxy.payload_bytes:,} bytes",
            f"- Serialize time: {dl.render_proxy.serialize_seconds:.6f}s",
            f"- **Note:** {dl.render_proxy.note}",
        ]
    )
    _write_markdown(path, lines)


def write_validation_report(bundle: EvaluationBundle, path: Path) -> None:
    report = bundle.validation
    lines = [
        "# SentinelAI Phase 8 — Validation Report",
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

    _write_markdown(path, lines)