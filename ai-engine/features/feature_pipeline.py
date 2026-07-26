from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

from features.device_features import extract_device_features
from features.entity_history import EntityHistoryTracker, build_entity_static_lookup
from features.feature_registry import FEATURE_NAMES
from features.geo_features import extract_geo_features, parse_country
from features.resource_features import extract_resource_features
from features.sequence_features import extract_sequence_features
from features.session_features import extract_session_features
from features.statistical_features import extract_statistical_features
from features.temporal_features import extract_temporal_features

REQUIRED_EVENT_COLUMNS: tuple[str, ...] = (
    "event_id",
    "timestamp",
    "entity_id",
    "entity_type",
    "source_ip",
    "geo_location",
    "resource_accessed",
    "auth_method",
    "session_duration",
    "command_sequence",
    "device_fingerprint",
    "login_result",
    "risk_context",
    "label",
)
OPTIONAL_EVENT_COLUMNS: tuple[str, ...] = ("device_os", "device_mac")


@dataclass(frozen=True)
class FeaturePipelineConfig:
    entities_path: Path
    events_path: Path
    ground_truth_path: Path | None = None
    output_dir: Path = field(default_factory=lambda: Path("data/features"))
    moving_average_window: int = 5
    drift_window: int = 10
    burst_window_minutes: float = 5.0
    confidence_saturation: int = 30


@dataclass(frozen=True)
class FeaturePipelineResult:
    engineered_df: pd.DataFrame
    input_event_count: int


class FeaturePipeline:
    """Consumes a Phase 2 (or Phase 2B) event log and produces one row of
    engineered behavioral features per event, computed strictly from each
    entity's history up to (not including) that event — never from the
    event's own outcome, and never from ground truth. Ground truth, when
    supplied, is attached to the output only as passthrough reference
    columns for downstream training/evaluation, never as a feature input.
    """

    def __init__(self, config: FeaturePipelineConfig) -> None:
        self.config = config

    def run(self) -> FeaturePipelineResult:
        entities_df = pd.read_csv(self.config.entities_path)
        events_df = pd.read_csv(self.config.events_path, low_memory=False)
        events_df["timestamp"] = pd.to_datetime(events_df["timestamp"], format="ISO8601")

        for column in OPTIONAL_EVENT_COLUMNS:
            if column not in events_df.columns:
                events_df[column] = None

        missing_required = [column for column in REQUIRED_EVENT_COLUMNS if column not in events_df.columns]
        if missing_required:
            raise ValueError(f"Events file is missing required columns: {missing_required}")

        static_lookup = build_entity_static_lookup(entities_df)
        events_sorted = events_df.sort_values(["entity_id", "timestamp"], kind="stable").reset_index(drop=True)

        trackers: dict[str, EntityHistoryTracker] = {}
        feature_rows: list[dict[str, object]] = []

        for row in events_sorted.itertuples(index=False):
            entity_id = str(row.entity_id)
            tracker = trackers.get(entity_id)
            if tracker is None:
                tracker = EntityHistoryTracker(
                    moving_average_window=self.config.moving_average_window,
                    drift_window=self.config.drift_window,
                    burst_window_minutes=self.config.burst_window_minutes,
                    confidence_saturation=self.config.confidence_saturation,
                )
                trackers[entity_id] = tracker

            static = static_lookup.get(entity_id)
            timestamp = row.timestamp.to_pydatetime() if hasattr(row.timestamp, "to_pydatetime") else row.timestamp
            session_duration = float(row.session_duration)
            geo_location = str(row.geo_location)
            country = parse_country(geo_location)
            resource_accessed = str(row.resource_accessed)
            device_fingerprint = str(row.device_fingerprint)
            device_os = row.device_os if isinstance(row.device_os, str) and row.device_os else None
            device_mac = row.device_mac if isinstance(row.device_mac, str) and row.device_mac else None
            auth_method = str(row.auth_method)
            login_result = str(row.login_result)

            features: dict[str, object] = {"event_id": row.event_id}
            features.update(extract_temporal_features(timestamp, session_duration, static, tracker))
            features.update(extract_geo_features(timestamp, geo_location, country, tracker))
            features.update(extract_device_features(device_fingerprint, device_os, device_mac, tracker))
            features.update(extract_session_features(tracker))
            features.update(extract_resource_features(resource_accessed, static, tracker))
            features.update(extract_sequence_features(row.command_sequence, timestamp, tracker))
            features.update(extract_statistical_features(session_duration, tracker))
            features.update(
                {
                    "history_length": tracker.history_length,
                    "new_entity_flag": tracker.is_new_entity,
                    "confidence_score": round(tracker.confidence_score, 4),
                }
            )
            feature_rows.append(features)

            tracker.update(
                timestamp=timestamp,
                resource_accessed=resource_accessed,
                device_fingerprint=device_fingerprint,
                device_os=device_os,
                device_mac=device_mac,
                geo_location=geo_location,
                country=country,
                auth_method=auth_method,
                login_result=login_result,
                session_duration=session_duration,
            )

        features_df = pd.DataFrame(feature_rows)
        engineered_df = events_sorted.merge(features_df, on="event_id", how="left")

        if self.config.ground_truth_path is not None:
            ground_truth_df = pd.read_csv(self.config.ground_truth_path, low_memory=False)
            # Only "is_attack" is genuinely new here — events_injected.csv (the
            # only events file ground truth is ever paired with) already
            # carries its own attack_type column; merging ground truth's copy
            # too would collide into confusing attack_type_x/attack_type_y.
            engineered_df = engineered_df.merge(
                ground_truth_df[["event_id", "is_attack"]], on="event_id", how="left"
            )
            engineered_df["is_attack"] = engineered_df["is_attack"].fillna(False)

        missing_features = [name for name in FEATURE_NAMES if name not in engineered_df.columns]
        if missing_features:
            raise RuntimeError(f"Pipeline output is missing registered features: {missing_features}")

        return FeaturePipelineResult(engineered_df=engineered_df, input_event_count=len(events_sorted))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Engineer behavioral features for a SentinelAI event dataset.")
    parser.add_argument("--entities", type=Path, required=True, help="Path to entities.csv (a Phase 2 run).")
    parser.add_argument("--events", type=Path, required=True, help="Path to events.csv or events_injected.csv.")
    parser.add_argument(
        "--ground-truth", type=Path, default=None, help="Optional path to ground_truth.csv (a Phase 2B run)."
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/features"))
    parser.add_argument("--moving-average-window", type=int, default=5)
    parser.add_argument("--drift-window", type=int, default=10)
    parser.add_argument("--burst-window-minutes", type=float, default=5.0)
    parser.add_argument("--confidence-saturation", type=int, default=30)
    parser.add_argument(
        "--verify-determinism",
        action="store_true",
        help="Run the pipeline twice and confirm identical output (slower; off by default).",
    )
    return parser


def main() -> None:
    from outputs.feature_writers import (
        write_engineered_dataset,
        write_feature_dictionary,
        write_feature_summary_report,
        write_validation_report,
    )
    from validators.feature_validators import run_all_feature_validations, validate_determinism

    args = build_arg_parser().parse_args()
    config = FeaturePipelineConfig(
        entities_path=args.entities,
        events_path=args.events,
        ground_truth_path=args.ground_truth,
        output_dir=args.output_dir,
        moving_average_window=args.moving_average_window,
        drift_window=args.drift_window,
        burst_window_minutes=args.burst_window_minutes,
        confidence_saturation=args.confidence_saturation,
    )

    print(f"Loading entities from: {config.entities_path}")
    print(f"Loading events from: {config.events_path}")
    result = FeaturePipeline(config).run()
    engineered_df = result.engineered_df
    print(f"Engineered {len(engineered_df):,} rows with {len(FEATURE_NAMES)} features.")

    validation_issues = list(
        run_all_feature_validations(engineered_df, expected_row_count=result.input_event_count).issues
    )

    if args.verify_determinism:
        print("Verifying determinism (running pipeline a second time)...")
        second_pass_df = FeaturePipeline(config).run().engineered_df
        validation_issues.extend(validate_determinism(engineered_df, second_pass_df))

    from validators.feature_validators import ValidationReport

    validation_report = ValidationReport(issues=tuple(validation_issues))

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = config.output_dir / run_id

    write_engineered_dataset(engineered_df, run_dir / "engineered_events.csv", run_dir / "engineered_events.parquet")
    write_feature_dictionary(run_dir / "feature_dictionary.md")
    write_feature_summary_report(run_dir / "feature_summary_report.md", engineered_df)
    write_validation_report(run_dir / "validation_report.md", validation_report)

    print(
        f"Validation: {'PASSED' if validation_report.passed else 'FAILED'} "
        f"({validation_report.error_count} errors, {validation_report.warning_count} warnings)"
    )
    print(f"Output written to: {run_dir.resolve()}")

    if not validation_report.passed:
        raise RuntimeError(
            f"Feature validation failed with {validation_report.error_count} error(s). "
            f"See {run_dir / 'validation_report.md'} for details."
        )


if __name__ == "__main__":
    main()