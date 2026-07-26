from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from profiles.profile_manager import BehaviourProfile, ProfileManager
from profiles.profile_storage import ProfileStorage
from profiles.relationship_profile import build_department_resource_index


@dataclass(frozen=True)
class BehaviourProfileEngineConfig:
    entities_path: Path
    engineered_events_path: Path
    storage_dir: Path = field(default_factory=lambda: Path("data/profiles/store"))
    output_dir: Path = field(default_factory=lambda: Path("data/profiles/runs"))
    confidence_saturation: int = 50
    adaptation_window_days: int = 30
    exclude_attacks: bool = True


@dataclass(frozen=True)
class BehaviourProfileEngineResult:
    profiles: list[BehaviourProfile]
    excluded_attack_events: int
    total_input_events: int
    known_entity_ids: set[str]
    previous_versions: dict[str, int]


class BehaviourProfileEngine:
    """Top-level orchestrator: loads entities + engineered events, filters
    to normal behavior, builds/updates one BehaviourProfile per entity via
    ProfileManager, persists every profile through ProfileStorage, and
    returns the full batch for reporting. Phase 2 / 2B / 2C are read-only
    inputs here — nothing in this class writes back into their data.
    """

    def __init__(self, config: BehaviourProfileEngineConfig) -> None:
        self.config = config
        self.storage = ProfileStorage(config.storage_dir)
        self.manager = ProfileManager(
            confidence_saturation=config.confidence_saturation,
            adaptation_window_days=config.adaptation_window_days,
        )

    def run(self) -> BehaviourProfileEngineResult:
        entities_df = pd.read_csv(self.config.entities_path)
        events_df = self._load_events()

        total_input_events = len(events_df)
        normal_events = self._filter_normal(events_df)
        excluded_attack_events = total_input_events - len(normal_events)

        department_by_entity = {
            str(row.entity_id): (str(row.department) if isinstance(row.department, str) and row.department else None)
            for row in entities_df.itertuples(index=False)
        }
        entity_type_by_entity = {
            str(row.entity_id): str(row.entity_type) for row in entities_df.itertuples(index=False)
        }
        known_entity_ids = set(department_by_entity.keys())

        events_by_entity = {
            str(entity_id): group for entity_id, group in normal_events.groupby("entity_id", sort=False)
        }
        department_resource_index = build_department_resource_index(events_by_entity, department_by_entity)

        now = datetime.now(timezone.utc)
        empty_events = normal_events.iloc[0:0]
        profiles: list[BehaviourProfile] = []
        previous_versions: dict[str, int] = {}

        for entity_id in sorted(known_entity_ids):
            entity_events = events_by_entity.get(entity_id, empty_events)
            entity_events_sorted = entity_events.sort_values("timestamp", kind="stable")
            department = department_by_entity.get(entity_id)
            department_common_resources = department_resource_index.get(department, ()) if department else ()

            existing_profile = self.storage.load_latest(entity_id)
            if existing_profile is not None:
                previous_versions[entity_id] = existing_profile.version

            profile = self.manager.build_profile(
                entity_id=entity_id,
                entity_type=entity_type_by_entity.get(entity_id, "unknown"),
                entity_events=entity_events,
                entity_events_sorted=entity_events_sorted,
                department=department,
                department_common_resources=department_common_resources,
                existing_profile=existing_profile,
                now=now,
            )

            self.storage.save(profile)
            profiles.append(profile)

        return BehaviourProfileEngineResult(
            profiles=profiles,
            excluded_attack_events=excluded_attack_events,
            total_input_events=total_input_events,
            known_entity_ids=known_entity_ids,
            previous_versions=previous_versions,
        )

    def _load_events(self) -> pd.DataFrame:
        path = self.config.engineered_events_path
        events_df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, low_memory=False)
        events_df["timestamp"] = pd.to_datetime(events_df["timestamp"], format="ISO8601")
        return events_df

    def _filter_normal(self, events_df: pd.DataFrame) -> pd.DataFrame:
        if not self.config.exclude_attacks:
            return events_df
        if "is_attack" in events_df.columns:
            return events_df[~events_df["is_attack"].astype(bool)].copy()
        if "label" in events_df.columns:
            return events_df[events_df["label"] != "attack"].copy()
        return events_df


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build/update SentinelAI behaviour profiles from engineered events.")
    parser.add_argument("--entities", type=Path, required=True, help="Path to entities.csv (a Phase 2 run).")
    parser.add_argument(
        "--events", type=Path, required=True, help="Path to engineered_events.csv or .parquet (a Phase 2C run)."
    )
    parser.add_argument("--storage-dir", type=Path, default=Path("data/profiles/store"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/profiles/runs"))
    parser.add_argument("--confidence-saturation", type=int, default=50)
    parser.add_argument("--adaptation-window-days", type=int, default=30)
    parser.add_argument(
        "--include-attacks",
        action="store_true",
        help="Do not exclude labeled attack events from profile learning (off by default).",
    )
    return parser


def main() -> None:
    from outputs.profile_writers import (
        write_behaviour_profiles,
        write_cold_start_report,
        write_drift_report,
        write_profile_summary,
        write_validation_report,
    )
    from validators.profile_validators import run_all_profile_validations

    args = build_arg_parser().parse_args()
    config = BehaviourProfileEngineConfig(
        entities_path=args.entities,
        engineered_events_path=args.events,
        storage_dir=args.storage_dir,
        output_dir=args.output_dir,
        confidence_saturation=args.confidence_saturation,
        adaptation_window_days=args.adaptation_window_days,
        exclude_attacks=not args.include_attacks,
    )

    print(f"Loading entities from: {config.entities_path}")
    print(f"Loading engineered events from: {config.engineered_events_path}")
    result = BehaviourProfileEngine(config).run()
    print(
        f"Built {len(result.profiles)} behaviour profiles from {result.total_input_events:,} events "
        f"({result.excluded_attack_events:,} labeled-attack events excluded)."
    )

    validation_report = run_all_profile_validations(
        result.profiles,
        known_entity_ids=result.known_entity_ids,
        previous_versions=result.previous_versions,
    )

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = config.output_dir / run_id

    write_behaviour_profiles(result.profiles, run_dir / "behaviour_profiles.json")
    write_profile_summary(result.profiles, run_dir / "profile_summary.csv")
    write_drift_report(result.profiles, run_dir / "drift_report.md")
    write_cold_start_report(result.profiles, run_dir / "cold_start_report.md")
    write_validation_report(validation_report, run_dir / "profile_validation_report.md")

    print(
        f"Validation: {'PASSED' if validation_report.passed else 'FAILED'} "
        f"({validation_report.error_count} errors, {validation_report.warning_count} warnings)"
    )
    print(f"Profile store: {config.storage_dir.resolve()}")
    print(f"Output written to: {run_dir.resolve()}")

    if not validation_report.passed:
        raise RuntimeError(
            f"Profile validation failed with {validation_report.error_count} error(s). "
            f"See {run_dir / 'profile_validation_report.md'} for details."
        )


if __name__ == "__main__":
    main()