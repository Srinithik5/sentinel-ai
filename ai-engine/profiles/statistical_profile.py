from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class StatisticalProfile:
    sample_count: int
    avg_login_hour: float
    login_hour_std: float
    avg_session_duration: float
    session_duration_std: float
    authentication_frequency_per_day: float
    failure_rate: float
    resource_frequency: dict[str, float]
    device_frequency: dict[str, float]
    geo_frequency: dict[str, float]
    working_hour_ratio: float

    def to_dict(self) -> dict[str, object]:
        return {
            "sample_count": self.sample_count,
            "avg_login_hour": self.avg_login_hour,
            "login_hour_std": self.login_hour_std,
            "avg_session_duration": self.avg_session_duration,
            "session_duration_std": self.session_duration_std,
            "authentication_frequency_per_day": self.authentication_frequency_per_day,
            "failure_rate": self.failure_rate,
            "resource_frequency": dict(self.resource_frequency),
            "device_frequency": dict(self.device_frequency),
            "geo_frequency": dict(self.geo_frequency),
            "working_hour_ratio": self.working_hour_ratio,
        }

    @staticmethod
    def from_dict(data: dict[str, object]) -> "StatisticalProfile":
        return StatisticalProfile(
            sample_count=int(data["sample_count"]),
            avg_login_hour=float(data["avg_login_hour"]),
            login_hour_std=float(data["login_hour_std"]),
            avg_session_duration=float(data["avg_session_duration"]),
            session_duration_std=float(data["session_duration_std"]),
            authentication_frequency_per_day=float(data["authentication_frequency_per_day"]),
            failure_rate=float(data["failure_rate"]),
            resource_frequency=dict(data["resource_frequency"]),
            device_frequency=dict(data["device_frequency"]),
            geo_frequency=dict(data["geo_frequency"]),
            working_hour_ratio=float(data["working_hour_ratio"]),
        )


_EMPTY_KWARGS: dict[str, object] = {
    "sample_count": 0,
    "avg_login_hour": 0.0,
    "login_hour_std": 0.0,
    "avg_session_duration": 0.0,
    "session_duration_std": 0.0,
    "authentication_frequency_per_day": 0.0,
    "failure_rate": 0.0,
    "resource_frequency": {},
    "device_frequency": {},
    "geo_frequency": {},
    "working_hour_ratio": 0.0,
}


def _normalized_value_counts(series: pd.Series) -> dict[str, float]:
    counts = series.value_counts(normalize=True)
    return {str(key): round(float(value), 4) for key, value in counts.items()}


def build_statistical_profile(entity_events: pd.DataFrame) -> StatisticalProfile:
    """Builds a StatisticalProfile from an entity's slice of normal
    (non-attack) events. Order-independent and deterministic — depends only
    on the event values themselves, never on row ordering.
    """
    sample_count = len(entity_events)
    if sample_count == 0:
        return StatisticalProfile(**_EMPTY_KWARGS)  # type: ignore[arg-type]

    login_hours = entity_events["login_hour"].astype(float)
    session_durations = entity_events["session_duration"].astype(float)

    timestamps = pd.to_datetime(entity_events["timestamp"], format="ISO8601")
    active_days = max(1, timestamps.dt.date.nunique())

    failure_rate = float((entity_events["login_result"] == "failure").mean())

    working_hour_ratio = (
        float((entity_events["working_hours_deviation"] == 0.0).mean())
        if "working_hours_deviation" in entity_events.columns
        else 0.0
    )

    return StatisticalProfile(
        sample_count=sample_count,
        avg_login_hour=round(float(login_hours.mean()), 4),
        login_hour_std=round(float(login_hours.std()), 4) if sample_count > 1 else 0.0,
        avg_session_duration=round(float(session_durations.mean()), 4),
        session_duration_std=round(float(session_durations.std()), 4) if sample_count > 1 else 0.0,
        authentication_frequency_per_day=round(sample_count / active_days, 4),
        failure_rate=round(failure_rate, 4),
        resource_frequency=_normalized_value_counts(entity_events["resource_accessed"]),
        device_frequency=_normalized_value_counts(entity_events["device_fingerprint"]),
        geo_frequency=_normalized_value_counts(entity_events["geo_location"]),
        working_hour_ratio=round(working_hour_ratio, 4),
    )