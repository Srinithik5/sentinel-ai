from __future__ import annotations

from pathlib import Path

from dashboard_export.dashboard_export_engine import DashboardExportBundle
from outputs.writers import write_json
from validators.dashboard_export_validator import ValidationReport

_FIXTURE_NAMES: tuple[str, ...] = ("overview.json", "alerts.json", "analytics.json", "mitre.json", "system_health.json")


def write_dashboard_fixtures(bundle: DashboardExportBundle, output_dir: Path) -> None:
    """Writes the 5 real JSON fixtures the Phase 7 frontend and Phase 8
    dashboard-latency benchmark consume. This is the primary deliverable
    of the export — everything else this module writes is provenance/
    audit trail alongside it, not a second copy of the same data.
    """
    write_json(bundle.overview.to_dict(), output_dir / "overview.json")
    write_json([alert.to_dict() for alert in bundle.alerts], output_dir / "alerts.json")
    write_json(bundle.analytics.to_dict(), output_dir / "analytics.json")
    write_json([entry.to_dict() for entry in bundle.mitre], output_dir / "mitre.json")
    write_json(bundle.system_health.to_dict(), output_dir / "system_health.json")


def write_export_summary(bundle: DashboardExportBundle, path: Path) -> None:
    """Provenance report: exactly which upstream run IDs and how many
    real records fed this fixture snapshot, and where it was written —
    written to `data/dashboard_export/<run_id>/`, separate from the
    fixtures themselves in `frontend/public/data/`.
    """
    lines = [
        "# SentinelAI — Dashboard Data Export Summary",
        "",
        "## Source Runs",
        "",
        f"- Detection: `{bundle.source_run_ids['detection']}` ({bundle.overview.total_events:,} events)",
        f"- Classification: `{bundle.source_run_ids['classification']}` ({len(bundle.alerts):,} alerts exported)",
        f"- Explainability: `{bundle.source_run_ids['explainability']}`",
        "",
        "## Fixture Contents",
        "",
        f"- `overview.json`: totalEvents={bundle.overview.total_events:,}, anomalies={bundle.overview.anomalies:,}, "
        f"detectionAccuracy={bundle.overview.detection_accuracy}%",
        f"- `alerts.json`: {len(bundle.alerts):,} alerts",
        f"- `analytics.json`: {len(bundle.analytics.attack_distribution)} attack types, "
        f"{len(bundle.analytics.hourly_activity)} hourly buckets",
        f"- `mitre.json`: {len(bundle.mitre)} attack-type reference entries",
        f"- `system_health.json`: detection/classification/explainability engine status",
        "",
        "## Note on Reproducibility",
        "",
        "Every field above is computed from real Phase 3/4/5/6 output files passed as CLI arguments — no "
        "synthetic, placeholder, or manually-entered values. `overview.json`'s `detectionLatencyMs` is a live "
        "wall-clock measurement (see `dashboard_export/overview_builder.py`) and will vary slightly between "
        "export runs, the same way Phase 8's streaming/scalability benchmarks do; every other field is exactly "
        "reproducible from the same input files.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_validation_report(report: ValidationReport, path: Path) -> None:
    lines = [
        "# SentinelAI — Dashboard Data Export Validation Report",
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
        for issue in report.issues:
            lines.append(f"| {issue.check} | {issue.severity} | {issue.message} |")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")