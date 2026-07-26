from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from detection.score_normalizer import clamp, normalize_circular_distance, normalize_frequency, normalize_zscore
from profiles.profile_manager import BehaviourProfile


@dataclass(frozen=True)
class EventRecord:
    """A typed, pandas-independent view of one incoming event to be scored
    — deliberately pulled from Phase 2C's own engineered columns (never
    recomputed), so Phase 4 never re-derives behavioral signals Phase 2C
    already produced.
    """

    event_id: str
    entity_id: str
    timestamp: datetime
    login_hour: int
    working_hours_deviation: float
    session_duration: float
    resource_accessed: str
    device_fingerprint: str
    geo_location: str
    auth_method: str
    login_result: str
    consecutive_failures: int
    fingerprint_mismatch: bool
    os_novelty: bool
    mac_novelty: bool
    geo_velocity_kmh: float
    burst_access_score: float


def event_record_from_row(row: object) -> EventRecord:
    timestamp = row.timestamp.to_pydatetime() if hasattr(row.timestamp, "to_pydatetime") else row.timestamp
    return EventRecord(
        event_id=str(row.event_id),
        entity_id=str(row.entity_id),
        timestamp=timestamp,
        login_hour=int(row.login_hour),
        working_hours_deviation=float(row.working_hours_deviation),
        session_duration=float(row.session_duration),
        resource_accessed=str(row.resource_accessed),
        device_fingerprint=str(row.device_fingerprint),
        geo_location=str(row.geo_location),
        auth_method=str(row.auth_method),
        login_result=str(row.login_result),
        consecutive_failures=int(row.consecutive_failures),
        fingerprint_mismatch=bool(row.fingerprint_mismatch),
        os_novelty=bool(row.os_novelty),
        mac_novelty=bool(row.mac_novelty),
        geo_velocity_kmh=float(row.geo_velocity_kmh),
        burst_access_score=float(row.burst_access_score),
    )


@dataclass(frozen=True)
class DimensionDeviation:
    dimension: str
    deviation_score: float
    detail: str

    def to_dict(self) -> dict[str, object]:
        return {"dimension": self.dimension, "deviation_score": self.deviation_score, "detail": self.detail}


_DIMENSIONS: tuple[str, ...] = ("temporal", "device", "resource", "geographic", "authentication", "session")
_WORKING_HOURS_DEVIATION_CAP = 12.0


class ProfileComparator:
    """Evaluates how much a single incoming event deviates from an entity's
    learned BehaviourProfile across six independent dimensions: temporal,
    device, resource, geographic, authentication, session. Every method
    here is a pure function of its inputs — no shared mutable state, no
    I/O — which is what makes each dimension trivially unit-testable in
    isolation from the rest of the detection pipeline.
    """

    def compare(
        self,
        event: EventRecord,
        profile: BehaviourProfile | None,
        *,
        previous_resource: str | None = None,
    ) -> tuple[DimensionDeviation, ...]:
        if profile is None:
            return self._unknown_profile_deviations()

        return (
            self._temporal_deviation(event, profile),
            self._device_deviation(event, profile),
            self._resource_deviation(event, profile, previous_resource),
            self._geographic_deviation(event, profile),
            self._authentication_deviation(event, profile),
            self._session_deviation(event, profile),
        )

    def _unknown_profile_deviations(self) -> tuple[DimensionDeviation, ...]:
        detail = "No behaviour profile exists yet for this entity — deviation is undefined, not assumed normal."
        return tuple(DimensionDeviation(dimension=name, deviation_score=0.5, detail=detail) for name in _DIMENSIONS)

    def _temporal_deviation(self, event: EventRecord, profile: BehaviourProfile) -> DimensionDeviation:
        stats = profile.statistical
        if stats.login_hour_std > 0:
            hour_score = normalize_zscore(float(event.login_hour), stats.avg_login_hour, stats.login_hour_std)
        else:
            hour_score = normalize_circular_distance(float(event.login_hour), stats.avg_login_hour, period=24.0)
        working_hours_score = clamp(event.working_hours_deviation / _WORKING_HOURS_DEVIATION_CAP)
        combined = round(max(hour_score, working_hours_score), 4)
        return DimensionDeviation(
            "temporal",
            combined,
            f"login_hour={event.login_hour} vs profile avg={stats.avg_login_hour:.2f} "
            f"(std={stats.login_hour_std:.2f}); working_hours_deviation={event.working_hours_deviation:.1f}h",
        )

    def _device_deviation(self, event: EventRecord, profile: BehaviourProfile) -> DimensionDeviation:
        frequency = profile.statistical.device_frequency.get(event.device_fingerprint, 0.0)
        score = round(normalize_frequency(frequency), 4)
        detail = (
            f"device seen in {frequency:.1%} of prior sessions" if frequency > 0 else "device never seen before"
        )
        return DimensionDeviation("device", score, detail)

    def _resource_deviation(
        self, event: EventRecord, profile: BehaviourProfile, previous_resource: str | None
    ) -> DimensionDeviation:
        frequency = profile.statistical.resource_frequency.get(event.resource_accessed, 0.0)
        frequency_deviation = normalize_frequency(frequency)

        if previous_resource is not None:
            transitions = profile.sequence.resource_transition_matrix.get(previous_resource, {})
            transition_probability = transitions.get(event.resource_accessed, 0.0)
            transition_deviation = normalize_frequency(transition_probability)
            combined = round((frequency_deviation + transition_deviation) / 2, 4)
            detail = (
                f"resource frequency={frequency:.1%}, transition probability from "
                f"'{previous_resource}'={transition_probability:.1%}"
            )
        else:
            combined = round(frequency_deviation, 4)
            detail = f"resource frequency={frequency:.1%} (no prior resource in this session to compare transition)"

        return DimensionDeviation("resource", combined, detail)

    def _geographic_deviation(self, event: EventRecord, profile: BehaviourProfile) -> DimensionDeviation:
        frequency = profile.statistical.geo_frequency.get(event.geo_location, 0.0)
        score = round(normalize_frequency(frequency), 4)
        detail = (
            f"location seen in {frequency:.1%} of prior sessions" if frequency > 0 else "location never seen before"
        )
        return DimensionDeviation("geographic", score, detail)

    def _authentication_deviation(self, event: EventRecord, profile: BehaviourProfile) -> DimensionDeviation:
        if event.login_result == "failure":
            score = round(1.0 - profile.statistical.failure_rate, 4)
            detail = f"login failed; entity's historical failure_rate={profile.statistical.failure_rate:.1%}"
        else:
            score = 0.0
            detail = "login succeeded"
        return DimensionDeviation("authentication", score, detail)

    def _session_deviation(self, event: EventRecord, profile: BehaviourProfile) -> DimensionDeviation:
        stats = profile.statistical
        score = round(normalize_zscore(event.session_duration, stats.avg_session_duration, stats.session_duration_std), 4)
        detail = (
            f"session_duration={event.session_duration:.1f}s vs profile avg={stats.avg_session_duration:.1f}s "
            f"(std={stats.session_duration_std:.1f})"
        )
        return DimensionDeviation("session", score, detail)