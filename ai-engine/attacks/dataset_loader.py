from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class EntityProfile:
    """A per-entity profile combining Phase 2's static entity attributes with
    behavior empirically observed in that entity's own event history (known
    devices, known source IPs). Attack modules target and impersonate real
    entities using this profile, never the raw locked Entity dataclass —
    this keeps Phase 2B fully decoupled from Phase 2's internal schema.
    """

    entity_id: str
    entity_type: str
    department: str | None
    role: str | None
    privilege_level: str
    home_location: str
    home_country: str
    timezone: str
    working_hours_start: int
    working_hours_end: int
    active_days: tuple[int, ...]
    normal_resources: tuple[str, ...]
    authentication_methods: tuple[str, ...]
    is_remote: bool
    network_cidr: str
    known_devices: tuple[str, ...]
    known_source_ips: tuple[str, ...]
    event_count: int
    first_seen: pd.Timestamp | None
    last_seen: pd.Timestamp | None

    def has_history(self) -> bool:
        return self.event_count > 0 and len(self.known_devices) > 0


@dataclass(frozen=True)
class LoadedDataset:
    run_dir: Path
    profiles: list[EntityProfile]
    entities_df: pd.DataFrame
    events_df: pd.DataFrame


def _clean_optional_str(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _split_pipe(value: object) -> tuple[str, ...]:
    if isinstance(value, str) and value:
        return tuple(value.split("|"))
    return ()


def _split_active_days(value: object) -> tuple[int, ...]:
    if isinstance(value, str) and value:
        return tuple(int(day) for day in value.split(","))
    return ()


def _build_entity_profiles(entities_df: pd.DataFrame, events_df: pd.DataFrame) -> list[EntityProfile]:
    device_map = events_df.groupby("entity_id")["device_fingerprint"].unique().apply(tuple).to_dict()
    ip_map = events_df.groupby("entity_id")["source_ip"].unique().apply(tuple).to_dict()
    count_map = events_df.groupby("entity_id").size().to_dict()
    first_seen_map = events_df.groupby("entity_id")["timestamp"].min().to_dict()
    last_seen_map = events_df.groupby("entity_id")["timestamp"].max().to_dict()

    profiles: list[EntityProfile] = []
    for row in entities_df.itertuples(index=False):
        entity_id = str(row.entity_id)
        profiles.append(
            EntityProfile(
                entity_id=entity_id,
                entity_type=str(row.entity_type),
                department=_clean_optional_str(row.department),
                role=_clean_optional_str(row.role),
                privilege_level=str(row.privilege_level),
                home_location=str(row.home_location),
                home_country=str(row.home_country),
                timezone=str(row.timezone),
                working_hours_start=int(row.working_hours_start),
                working_hours_end=int(row.working_hours_end),
                active_days=_split_active_days(row.active_days),
                normal_resources=_split_pipe(row.normal_resources),
                authentication_methods=_split_pipe(row.authentication_methods),
                is_remote=bool(row.is_remote),
                network_cidr=str(row.network_cidr),
                known_devices=device_map.get(entity_id, ()),
                known_source_ips=ip_map.get(entity_id, ()),
                event_count=int(count_map.get(entity_id, 0)),
                first_seen=first_seen_map.get(entity_id),
                last_seen=last_seen_map.get(entity_id),
            )
        )
    return profiles


def load_dataset(run_dir: Path) -> LoadedDataset:
    entities_path = run_dir / "entities.csv"
    events_path = run_dir / "events.csv"

    if not entities_path.exists() or not events_path.exists():
        raise FileNotFoundError(
            f"Expected entities.csv and events.csv under {run_dir} — "
            f"point --dataset-dir at a Phase 2 generate_dataset.py run directory."
        )

    entities_df = pd.read_csv(entities_path)
    events_df = pd.read_csv(events_path)
    events_df["timestamp"] = pd.to_datetime(events_df["timestamp"], format="ISO8601")

    profiles = _build_entity_profiles(entities_df, events_df)

    return LoadedDataset(run_dir=run_dir, profiles=profiles, entities_df=entities_df, events_df=events_df)