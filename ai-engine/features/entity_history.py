from __future__ import annotations

import bisect
from collections import deque
from dataclasses import dataclass
from datetime import datetime

import pandas as pd


@dataclass(frozen=True)
class EntityStaticProfile:
    """The subset of an entity's static Phase 2 attributes feature
    extractors need. Built once from entities.csv, independent of the
    locked Entity dataclass.
    """

    entity_id: str
    entity_type: str
    department: str | None
    role: str | None
    privilege_level: str
    working_hours_start: int
    working_hours_end: int
    active_days: tuple[int, ...]
    timezone: str
    is_remote: bool
    home_country: str


def _split_active_days(value: object) -> tuple[int, ...]:
    if isinstance(value, str) and value:
        return tuple(int(day) for day in value.split(","))
    return ()


def _clean_optional(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def build_entity_static_lookup(entities_df: pd.DataFrame) -> dict[str, EntityStaticProfile]:
    lookup: dict[str, EntityStaticProfile] = {}
    for row in entities_df.itertuples(index=False):
        entity_id = str(row.entity_id)
        lookup[entity_id] = EntityStaticProfile(
            entity_id=entity_id,
            entity_type=str(row.entity_type),
            department=_clean_optional(row.department),
            role=_clean_optional(row.role),
            privilege_level=str(row.privilege_level),
            working_hours_start=int(row.working_hours_start),
            working_hours_end=int(row.working_hours_end),
            active_days=_split_active_days(row.active_days),
            timezone=str(row.timezone),
            is_remote=bool(row.is_remote),
            home_country=str(row.home_country),
        )
    return lookup


class EntityHistoryTracker:
    """Running, causally-safe state for one entity, updated as its events
    are processed in chronological order.

    Every query method (the properties and the `is_*`/`*_score` methods)
    reflects only events strictly BEFORE the one currently being featured.
    `update()` must be called only AFTER features for the current event
    have been extracted — this ordering is what prevents label/feature
    leakage from the current event into its own "historical" features.
    """

    def __init__(
        self,
        *,
        moving_average_window: int = 5,
        drift_window: int = 10,
        burst_window_minutes: float = 5.0,
        confidence_saturation: int = 30,
    ) -> None:
        self.moving_average_window = moving_average_window
        self.drift_window = drift_window
        self.burst_window_minutes = burst_window_minutes
        self.confidence_saturation = confidence_saturation

        self.history_length: int = 0
        self.success_count: int = 0
        self.failure_count: int = 0
        self.mfa_count: int = 0
        self.consecutive_failures: int = 0

        self.known_resources: set[str] = set()
        self.known_devices: set[str] = set()
        self.known_os: set[str] = set()
        self.known_mac: set[str] = set()
        self.known_cities: set[str] = set()
        self.known_countries: set[str] = set()
        self.city_change_count: int = 0

        self.last_timestamp: datetime | None = None
        self.last_geo_location: str | None = None
        self.last_country: str | None = None

        self._device_counts: dict[str, int] = {}
        self._sorted_durations: list[float] = []
        self._welford_mean: float = 0.0
        self._welford_m2: float = 0.0
        self._moving_window: deque[float] = deque(maxlen=moving_average_window)

        self._recent_resource_window: deque[str] = deque(maxlen=drift_window)
        self._baseline_resources: set[str] = set()

        self._recent_event_timestamps: deque[datetime] = deque()

    # ---- read-only queries: reflect only events strictly before "now" ----

    @property
    def is_new_entity(self) -> bool:
        return self.history_length == 0

    @property
    def success_ratio(self) -> float:
        return self.success_count / self.history_length if self.history_length else 0.0

    @property
    def failure_ratio(self) -> float:
        return self.failure_count / self.history_length if self.history_length else 0.0

    @property
    def mfa_usage_frequency(self) -> float:
        return self.mfa_count / self.history_length if self.history_length else 0.0

    @property
    def rolling_mean_session_duration(self) -> float:
        return self._welford_mean if self.history_length > 0 else 0.0

    @property
    def rolling_std_session_duration(self) -> float:
        if self.history_length < 2:
            return 0.0
        variance = self._welford_m2 / (self.history_length - 1)
        return variance**0.5

    @property
    def moving_avg_session_duration(self) -> float:
        if not self._moving_window:
            return 0.0
        return sum(self._moving_window) / len(self._moving_window)

    @property
    def city_change_frequency(self) -> float:
        return self.city_change_count / self.history_length if self.history_length else 0.0

    @property
    def resource_diversity(self) -> float:
        return len(self.known_resources) / self.history_length if self.history_length else 0.0

    @property
    def confidence_score(self) -> float:
        return min(1.0, self.history_length / self.confidence_saturation)

    def time_since_previous_login_seconds(self, current_timestamp: datetime) -> float:
        if self.last_timestamp is None:
            return -1.0
        return (current_timestamp - self.last_timestamp).total_seconds()

    def session_duration_zscore(self, current_duration: float) -> float:
        std = self.rolling_std_session_duration
        if self.history_length < 2 or std == 0.0:
            return 0.0
        return (current_duration - self.rolling_mean_session_duration) / std

    def historical_percentile(self, current_duration: float) -> float:
        if not self._sorted_durations:
            return 50.0
        rank = bisect.bisect_right(self._sorted_durations, current_duration)
        return 100.0 * rank / len(self._sorted_durations)

    def is_resource_novel(self, resource: str) -> bool:
        return resource not in self.known_resources

    def is_device_novel(self, device_fingerprint: str) -> bool:
        return device_fingerprint not in self.known_devices

    def device_familiarity_score(self, device_fingerprint: str) -> float:
        if self.history_length == 0:
            return 0.0
        return self._device_counts.get(device_fingerprint, 0) / self.history_length

    def is_os_novel(self, os_value: str | None) -> bool:
        return bool(os_value) and os_value not in self.known_os

    def is_mac_novel(self, mac_value: str | None) -> bool:
        return bool(mac_value) and mac_value not in self.known_mac

    def is_geo_novel(self, geo_location: str) -> bool:
        return geo_location not in self.known_cities

    def burst_access_score(self, current_timestamp: datetime) -> float:
        threshold = current_timestamp - pd.Timedelta(minutes=self.burst_window_minutes)
        while self._recent_event_timestamps and self._recent_event_timestamps[0] < threshold:
            self._recent_event_timestamps.popleft()
        return float(len(self._recent_event_timestamps))

    def behaviour_drift_score(self) -> float:
        recent_set = set(self._recent_resource_window)
        if not recent_set:
            return 0.0
        novel = recent_set - self._baseline_resources
        return len(novel) / len(recent_set)

    # ---- mutation: call only AFTER features for the current event are extracted ----

    def update(
        self,
        *,
        timestamp: datetime,
        resource_accessed: str,
        device_fingerprint: str,
        device_os: str | None,
        device_mac: str | None,
        geo_location: str,
        country: str,
        auth_method: str,
        login_result: str,
        session_duration: float,
    ) -> None:
        self.history_length += 1

        delta = session_duration - self._welford_mean
        self._welford_mean += delta / self.history_length
        delta2 = session_duration - self._welford_mean
        self._welford_m2 += delta * delta2

        bisect.insort(self._sorted_durations, session_duration)
        self._moving_window.append(session_duration)

        if login_result == "success":
            self.success_count += 1
            self.consecutive_failures = 0
        else:
            self.failure_count += 1
            self.consecutive_failures += 1

        if auth_method == "mfa":
            self.mfa_count += 1

        if self.last_geo_location is not None and geo_location != self.last_geo_location:
            self.city_change_count += 1
        self.known_cities.add(geo_location)
        self.known_countries.add(country)
        self.last_geo_location = geo_location
        self.last_country = country

        self._device_counts[device_fingerprint] = self._device_counts.get(device_fingerprint, 0) + 1
        self.known_devices.add(device_fingerprint)
        if device_os:
            self.known_os.add(device_os)
        if device_mac:
            self.known_mac.add(device_mac)

        if len(self._recent_resource_window) == self._recent_resource_window.maxlen:
            oldest = self._recent_resource_window[0]
            self._baseline_resources.add(oldest)
        self._recent_resource_window.append(resource_accessed)
        self.known_resources.add(resource_accessed)

        self._recent_event_timestamps.append(timestamp)
        self.last_timestamp = timestamp