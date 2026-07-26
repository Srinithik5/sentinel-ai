from __future__ import annotations

import random
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, time, timezone
from enum import Enum
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from attacks.dataset_loader import EntityProfile
from utils.network import OFFICES
from utils.time_utils import date_range as _date_range

# RFC 5737 TEST-NET-2 — reserved for documentation/examples, so no injected
# attacker IP could resemble a real organization's public IP space.
ATTACKER_NETWORK_CIDR = "198.51.100.0/24"


class AttackSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class AttackConfig:
    enabled: bool = True
    injection_percentage: float = 0.02
    severity: AttackSeverity = AttackSeverity.MEDIUM
    intensity: float = 1.0
    random_seed: int = 42

    def __post_init__(self) -> None:
        if not 0.0 <= self.injection_percentage <= 1.0:
            raise ValueError("injection_percentage must be between 0.0 and 1.0")
        if self.intensity <= 0.0:
            raise ValueError("intensity must be greater than 0.0")


@dataclass(frozen=True)
class AttackMetadata:
    attack_id: str
    attack_type: str
    severity: str
    mitre_tactic: str
    mitre_technique: str
    confidence: float
    injected: bool
    description: str


@dataclass(frozen=True)
class InjectedEvent:
    event_id: str
    timestamp: datetime
    entity_id: str
    entity_type: str
    source_ip: str
    geo_location: str
    resource_accessed: str
    auth_method: str
    session_duration: int
    command_sequence: tuple[str, ...]
    device_fingerprint: str
    login_result: str
    risk_context: str
    label: str
    metadata: AttackMetadata
    device_os: str | None = None
    device_mac: str | None = None

    def to_row(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "source_ip": self.source_ip,
            "geo_location": self.geo_location,
            "resource_accessed": self.resource_accessed,
            "auth_method": self.auth_method,
            "session_duration": self.session_duration,
            "command_sequence": "|".join(self.command_sequence),
            "device_fingerprint": self.device_fingerprint,
            "login_result": self.login_result,
            "risk_context": self.risk_context,
            "label": self.label,
            "device_os": self.device_os,
            "device_mac": self.device_mac,
            "attack_id": self.metadata.attack_id,
            "attack_type": self.metadata.attack_type,
            "severity": self.metadata.severity,
            "mitre_tactic": self.metadata.mitre_tactic,
            "mitre_technique": self.metadata.mitre_technique,
            "confidence": self.metadata.confidence,
            "injected": self.metadata.injected,
            "description": self.metadata.description,
        }


INJECTED_EVENT_COLUMNS: tuple[str, ...] = (
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
    "device_os",
    "device_mac",
    "attack_id",
    "attack_type",
    "severity",
    "mitre_tactic",
    "mitre_technique",
    "confidence",
    "injected",
    "description",
)


@dataclass(frozen=True)
class AttackInjectionResult:
    attack_type: str
    events: tuple[InjectedEvent, ...]
    targeted_entity_ids: tuple[str, ...]

    @property
    def event_count(self) -> int:
        return len(self.events)

    @property
    def incident_count(self) -> int:
        return len(self.targeted_entity_ids)


def generate_attack_id() -> str:
    return f"atk-{uuid.uuid4().hex[:12]}"


def generate_attack_event_id() -> str:
    return f"aevt-{uuid.uuid4().hex[:16]}"


def is_within_working_hours(profile: EntityProfile, timestamp: datetime) -> bool:
    local_dt = timestamp.astimezone(ZoneInfo(profile.timezone))
    return (
        local_dt.weekday() in profile.active_days
        and profile.working_hours_start <= local_dt.hour < profile.working_hours_end
    )


def dataset_end_boundary(events_df: pd.DataFrame) -> datetime:
    """The last instant covered by the dataset's declared date range (end of
    the last calendar day with events, UTC). Attacks that anchor a new event
    to "shortly after this entity's last known event" must stay within this
    boundary, or chronological-consistency validation correctly rejects
    them as extending the dataset past its own declared range.
    """
    last_date = events_df["timestamp"].max().date()
    return datetime.combine(last_date, time.max, tzinfo=timezone.utc)


def safe_local_day_range(events_df: pd.DataFrame) -> list:
    """Calendar days safe to anchor a *local*-time event to before converting
    to UTC (e.g. via random_timestamp_at_hour/random_business_timestamp).

    A local day+hour near the dataset's first or last day can convert to a
    UTC timestamp on the adjacent calendar day whenever the entity's
    timezone offset is nonzero — spilling outside the dataset's declared
    [start_date, end_date] range. Trimming one day off each edge is a safe
    margin for any real-world UTC offset (max ±14h) and is far simpler than
    computing an exact per-timezone bound.
    """
    start_date = events_df["timestamp"].min().date()
    end_date = events_df["timestamp"].max().date()
    full_range = _date_range(start_date, end_date)
    if len(full_range) <= 2:
        return full_range
    return full_range[1:-1]


def pick_foreign_location(home_location: str, rng: random.Random) -> str:
    candidates = [
        f"{office.city}, {office.country}"
        for office in OFFICES
        if f"{office.city}, {office.country}" != home_location
    ]
    if not candidates:
        return home_location
    return rng.choice(candidates)


def compute_attack_risk_context(
    *,
    is_working_time: bool,
    is_remote: bool,
    is_known_device: bool,
    is_expected_resource: bool,
) -> str:
    tags = [
        "in_hours" if is_working_time else "off_hours",
        "remote_location" if is_remote else "home_location",
        "known_device" if is_known_device else "unrecognized_device",
        "expected_resource" if is_expected_resource else "unlisted_resource",
    ]
    return "|".join(tags)


class AttackModule(ABC):
    """Template-method base for every attack: subclasses only decide *who*
    to target and *what one incident looks like*; scheduling, metadata
    generation, and result aggregation are handled uniformly here so every
    attack module is independent (SRP) yet interchangeable to the
    orchestrator (LSP/DIP) without it knowing any attack-specific logic.
    """

    attack_type: str
    mitre_tactic: str
    mitre_technique: str

    def __init__(self, config: AttackConfig) -> None:
        self.config = config
        self._rng = random.Random(config.random_seed)
        self._np_rng = np.random.default_rng(config.random_seed)

    @abstractmethod
    def select_targets(self, profiles: list[EntityProfile], events_df: pd.DataFrame) -> list[EntityProfile]:
        """Choose which entities this attack will target."""

    @abstractmethod
    def generate_incident(
        self,
        profile: EntityProfile,
        events_df: pd.DataFrame,
        incident_index: int,
    ) -> list[InjectedEvent]:
        """Generate the sequence of injected events representing one attack incident."""

    def inject(self, profiles: list[EntityProfile], events_df: pd.DataFrame) -> AttackInjectionResult:
        if not self.config.enabled:
            return AttackInjectionResult(attack_type=self.attack_type, events=(), targeted_entity_ids=())

        targets = self.select_targets(profiles, events_df)
        generated: list[InjectedEvent] = []
        for index, profile in enumerate(targets):
            generated.extend(self.generate_incident(profile, events_df, index))

        return AttackInjectionResult(
            attack_type=self.attack_type,
            events=tuple(generated),
            targeted_entity_ids=tuple(profile.entity_id for profile in targets),
        )

    def _sample_targets(self, eligible: list[EntityProfile], minimum: int = 1) -> list[EntityProfile]:
        if not eligible:
            return []
        target_count = max(minimum, round(self.config.injection_percentage * len(eligible)))
        target_count = min(target_count, len(eligible))
        return self._rng.sample(eligible, k=target_count)

    def _make_metadata(self, confidence: float, description: str) -> AttackMetadata:
        return AttackMetadata(
            attack_id=generate_attack_id(),
            attack_type=self.attack_type,
            severity=self.config.severity.value,
            mitre_tactic=self.mitre_tactic,
            mitre_technique=self.mitre_technique,
            confidence=round(confidence, 3),
            injected=True,
            description=description,
        )