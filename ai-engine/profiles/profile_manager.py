from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

import pandas as pd

from profiles.drift_profile import DriftProfile, compute_drift
from profiles.relationship_profile import RelationshipProfile, build_relationship_profile
from profiles.sequence_profile import SequenceProfile, build_sequence_profile
from profiles.statistical_profile import StatisticalProfile, build_statistical_profile


class WarmupStrategy(str, Enum):
    INSUFFICIENT_DATA = "insufficient_data"
    WARMING_UP = "warming_up"
    ESTABLISHED = "established"


_INSUFFICIENT_DATA_THRESHOLD = 5


@dataclass(frozen=True)
class ColdStartStatus:
    history_length: int
    is_new_entity: bool
    confidence_score: float
    warmup_strategy: WarmupStrategy

    def to_dict(self) -> dict[str, object]:
        return {
            "history_length": self.history_length,
            "is_new_entity": self.is_new_entity,
            "confidence_score": self.confidence_score,
            "warmup_strategy": self.warmup_strategy.value,
        }

    @staticmethod
    def from_dict(data: dict[str, object]) -> "ColdStartStatus":
        return ColdStartStatus(
            history_length=int(data["history_length"]),
            is_new_entity=bool(data["is_new_entity"]),
            confidence_score=float(data["confidence_score"]),
            warmup_strategy=WarmupStrategy(data["warmup_strategy"]),
        )


def build_cold_start_status(sample_count: int, *, confidence_saturation: int) -> ColdStartStatus:
    if sample_count <= 0:
        return ColdStartStatus(0, True, 0.0, WarmupStrategy.INSUFFICIENT_DATA)

    confidence_score = round(min(1.0, sample_count / confidence_saturation), 4)
    if sample_count < _INSUFFICIENT_DATA_THRESHOLD:
        strategy = WarmupStrategy.INSUFFICIENT_DATA
    elif sample_count < confidence_saturation:
        strategy = WarmupStrategy.WARMING_UP
    else:
        strategy = WarmupStrategy.ESTABLISHED

    return ColdStartStatus(sample_count, False, confidence_score, strategy)


@dataclass(frozen=True)
class BehaviourProfile:
    entity_id: str
    entity_type: str
    version: int
    created_at: datetime
    updated_at: datetime
    statistical: StatisticalProfile
    sequence: SequenceProfile
    relationship: RelationshipProfile
    drift: DriftProfile
    cold_start: ColdStartStatus

    def to_dict(self) -> dict[str, object]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "statistical": self.statistical.to_dict(),
            "sequence": self.sequence.to_dict(),
            "relationship": self.relationship.to_dict(),
            "drift": self.drift.to_dict(),
            "cold_start": self.cold_start.to_dict(),
        }

    @staticmethod
    def from_dict(data: dict[str, object]) -> "BehaviourProfile":
        return BehaviourProfile(
            entity_id=str(data["entity_id"]),
            entity_type=str(data["entity_type"]),
            version=int(data["version"]),
            created_at=datetime.fromisoformat(str(data["created_at"])),
            updated_at=datetime.fromisoformat(str(data["updated_at"])),
            statistical=StatisticalProfile.from_dict(data["statistical"]),
            sequence=SequenceProfile.from_dict(data["sequence"]),
            relationship=RelationshipProfile.from_dict(data["relationship"]),
            drift=DriftProfile.from_dict(data["drift"]),
            cold_start=ColdStartStatus.from_dict(data["cold_start"]),
        )


class ProfileManager:
    """Owns the lifecycle of a single entity's BehaviourProfile: building a
    fresh one from data, comparing it against any previously stored version
    to compute drift, and bumping the version number. Persistence itself is
    delegated to ProfileStorage — this class is pure logic, no I/O, which
    is what makes it trivially unit-testable.
    """

    def __init__(self, *, confidence_saturation: int = 50, adaptation_window_days: int = 30) -> None:
        self.confidence_saturation = confidence_saturation
        self.adaptation_window_days = adaptation_window_days

    def build_profile(
        self,
        *,
        entity_id: str,
        entity_type: str,
        entity_events: pd.DataFrame,
        entity_events_sorted: pd.DataFrame,
        department: str | None,
        department_common_resources: tuple[str, ...],
        existing_profile: BehaviourProfile | None,
        now: datetime | None = None,
    ) -> BehaviourProfile:
        now = now or datetime.now(timezone.utc)

        statistical = build_statistical_profile(entity_events)
        sequence = build_sequence_profile(entity_events_sorted)
        relationship = build_relationship_profile(
            entity_events, department=department, department_common_resources=department_common_resources
        )
        cold_start = build_cold_start_status(
            statistical.sample_count, confidence_saturation=self.confidence_saturation
        )

        previous_version = existing_profile.version if existing_profile is not None else 0
        historical_statistical = existing_profile.statistical if existing_profile is not None else None
        drift = compute_drift(
            historical=historical_statistical,
            current=statistical,
            previous_version=previous_version,
            adaptation_window_days=self.adaptation_window_days,
        )

        created_at = existing_profile.created_at if existing_profile is not None else now

        return BehaviourProfile(
            entity_id=entity_id,
            entity_type=entity_type,
            version=drift.profile_version,
            created_at=created_at,
            updated_at=now,
            statistical=statistical,
            sequence=sequence,
            relationship=relationship,
            drift=drift,
            cold_start=cold_start,
        )