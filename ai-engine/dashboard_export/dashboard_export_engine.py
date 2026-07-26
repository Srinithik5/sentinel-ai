from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

from dashboard_export.alerts_builder import Alert, build_alerts
from dashboard_export.analytics_builder import AnalyticsData, build_analytics
from dashboard_export.mitre_builder import MitreEntry, build_mitre_entries
from dashboard_export.overview_builder import OverviewMetrics, build_overview
from dashboard_export.system_health_builder import SystemHealthData, build_system_health
from profiles.profile_storage import ProfileStorage

_DEFAULT_SAMPLE_PER_ATTACK_TYPE = 45
_DEFAULT_HISTORY_WINDOW = 12
_DEFAULT_LATENCY_SAMPLE_SIZE = 2000


@dataclass(frozen=True)
class DashboardExportConfig:
    detection_results_path: Path
    classification_results_path: Path
    explainability_dir: Path
    engineered_events_path: Path
    entities_path: Path
    profile_store_dir: Path
    output_dir: Path
    export_run_output_dir: Path = field(default_factory=lambda: Path("data/dashboard_export"))
    sample_per_attack_type: int = _DEFAULT_SAMPLE_PER_ATTACK_TYPE
    history_window: int = _DEFAULT_HISTORY_WINDOW
    latency_sample_size: int = _DEFAULT_LATENCY_SAMPLE_SIZE


@dataclass(frozen=True)
class DashboardExportBundle:
    overview: OverviewMetrics
    alerts: tuple[Alert, ...]
    analytics: AnalyticsData
    mitre: tuple[MitreEntry, ...]
    system_health: SystemHealthData
    source_run_ids: dict[str, str]


class DashboardExportEngine:
    """Reads the real Phase 3/4/5/6 output files for one set of pipeline
    runs and builds the 5 dashboard fixtures the Phase 7 frontend and
    Phase 8 dashboard-latency benchmark consume. Read-only against every
    upstream phase — writes nothing back into `ai-engine/data/`, and does
    not modify any phase's own output.
    """

    def __init__(self, config: DashboardExportConfig) -> None:
        self.config = config

    def run(self) -> DashboardExportBundle:
        c = self.config

        detection_df = pd.read_csv(c.detection_results_path, low_memory=False)
        detection_df["timestamp"] = pd.to_datetime(detection_df["timestamp"], format="ISO8601")

        classification_df = pd.read_csv(c.classification_results_path, low_memory=False)
        classification_df["timestamp"] = pd.to_datetime(classification_df["timestamp"], format="ISO8601")

        analyst_summary_df = pd.read_csv(c.explainability_dir / "analyst_summary.csv", low_memory=False)
        explainability_report_df = pd.read_csv(c.explainability_dir / "explainability_report.csv", low_memory=False)

        events_df = (
            pd.read_parquet(c.engineered_events_path)
            if c.engineered_events_path.suffix == ".parquet"
            else pd.read_csv(c.engineered_events_path, low_memory=False)
        )
        events_df["timestamp"] = pd.to_datetime(events_df["timestamp"], format="ISO8601")

        entities_df = pd.read_csv(c.entities_path, low_memory=False)
        profile_store = ProfileStorage(c.profile_store_dir)

        overview = build_overview(
            detection_df,
            engineered_events_path=c.engineered_events_path,
            profile_store_dir=c.profile_store_dir,
            latency_sample_size=c.latency_sample_size,
        )

        alerts = build_alerts(
            classification_df=classification_df,
            detection_df=detection_df,
            analyst_summary_df=analyst_summary_df,
            explainability_report_df=explainability_report_df,
            events_df=events_df,
            entities_df=entities_df,
            profile_store=profile_store,
            sample_per_attack_type=c.sample_per_attack_type,
            history_window=c.history_window,
        )

        analytics = build_analytics(detection_df, classification_df, events_df)
        mitre = build_mitre_entries()

        system_health = build_system_health(
            detection_results_path=c.detection_results_path,
            detection_event_count=len(detection_df),
            classification_results_path=c.classification_results_path,
            classification_event_count=len(classification_df),
            explainability_dir=c.explainability_dir,
            explainability_event_count=len(analyst_summary_df),
        )

        return DashboardExportBundle(
            overview=overview,
            alerts=alerts,
            analytics=analytics,
            mitre=mitre,
            system_health=system_health,
            source_run_ids={
                "detection": c.detection_results_path.parent.name,
                "classification": c.classification_results_path.parent.name,
                "explainability": c.explainability_dir.name,
            },
        )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export real Phase 3/4/5/6 output into the dashboard JSON fixtures consumed by the "
        "Phase 7 frontend and the Phase 8 dashboard-latency benchmark."
    )
    parser.add_argument("--detection-results", type=Path, required=True, help="Path to detection_results.csv (a Phase 4 run).")
    parser.add_argument("--classification-results", type=Path, required=True, help="Path to classification_report.csv (a Phase 5 run).")
    parser.add_argument("--explainability-dir", type=Path, required=True, help="Path to a Phase 6 run directory (contains analyst_summary.csv and explainability_report.csv).")
    parser.add_argument("--events", type=Path, required=True, help="Path to engineered_events.csv/.parquet (a Phase 2C run).")
    parser.add_argument("--entities", type=Path, required=True, help="Path to entities.csv (a Phase 2 run).")
    parser.add_argument("--profile-store", type=Path, required=True, help="Path to the Phase 3 profile store directory.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory the 5 JSON fixtures are written into (e.g. ../frontend/public/data).")
    parser.add_argument("--export-run-output-dir", type=Path, default=Path("data/dashboard_export"), help="Where this run's provenance/validation reports are written.")
    parser.add_argument("--sample-per-attack-type", type=int, default=_DEFAULT_SAMPLE_PER_ATTACK_TYPE)
    parser.add_argument("--history-window", type=int, default=_DEFAULT_HISTORY_WINDOW)
    parser.add_argument("--latency-sample-size", type=int, default=_DEFAULT_LATENCY_SAMPLE_SIZE)
    return parser


def main() -> None:
    from outputs.dashboard_export_writers import write_dashboard_fixtures, write_export_summary, write_validation_report
    from validators.dashboard_export_validator import run_all_dashboard_export_validations

    args = build_arg_parser().parse_args()
    config = DashboardExportConfig(
        detection_results_path=args.detection_results,
        classification_results_path=args.classification_results,
        explainability_dir=args.explainability_dir,
        engineered_events_path=args.events,
        entities_path=args.entities,
        profile_store_dir=args.profile_store,
        output_dir=args.output_dir,
        export_run_output_dir=args.export_run_output_dir,
        sample_per_attack_type=args.sample_per_attack_type,
        history_window=args.history_window,
        latency_sample_size=args.latency_sample_size,
    )

    print("Exporting dashboard fixtures...")
    engine = DashboardExportEngine(config)
    bundle = engine.run()

    validation = run_all_dashboard_export_validations(
        overview=bundle.overview,
        alerts=bundle.alerts,
        analytics=bundle.analytics,
        mitre=bundle.mitre,
        system_health=bundle.system_health,
    )

    print(f"Overview: totalEvents={bundle.overview.total_events:,} anomalies={bundle.overview.anomalies:,} "
          f"detectionAccuracy={bundle.overview.detection_accuracy}% detectionLatencyMs={bundle.overview.detection_latency_ms}")
    print(f"Alerts exported: {len(bundle.alerts):,}")
    print(f"MITRE entries: {len(bundle.mitre)}")
    print(
        f"Validation: {'PASSED' if validation.passed else 'FAILED'} "
        f"({validation.error_count} errors, {validation.warning_count} warnings)"
    )

    if not validation.passed:
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        failure_report_path = config.export_run_output_dir / run_id / "dashboard_export_validation_report.md"
        write_validation_report(validation, failure_report_path)
        raise RuntimeError(
            f"Dashboard export validation failed with {validation.error_count} error(s). "
            f"See {failure_report_path} for details. Fixtures were NOT written to {config.output_dir}."
        )

    write_dashboard_fixtures(bundle, config.output_dir)

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = config.export_run_output_dir / run_id
    write_export_summary(bundle, run_dir / "export_summary.md")
    write_validation_report(validation, run_dir / "dashboard_export_validation_report.md")

    print(f"Fixtures written to: {config.output_dir.resolve()}")
    print(f"Export report written to: {run_dir.resolve()}")


if __name__ == "__main__":
    main()