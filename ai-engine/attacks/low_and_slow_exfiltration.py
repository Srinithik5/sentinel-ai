from __future__ import annotations

import pandas as pd

from attacks.base import (
    AttackModule,
    InjectedEvent,
    compute_attack_risk_context,
    generate_attack_event_id,
    safe_local_day_range,
)
from attacks.dataset_loader import EntityProfile
from utils.time_utils import random_timestamp_at_hour


class LowAndSlowExfiltrationAttack(AttackModule):
    """Many small off-hours sessions against the same resource spread over
    a long duration, with session length gradually increasing — designed
    to stay under any single-session detection threshold.
    """

    attack_type = "low_and_slow_exfiltration"
    mitre_tactic = "Exfiltration"
    mitre_technique = "T1030 Data Transfer Size Limits"

    _MIN_SESSIONS = 8
    _MAX_SESSIONS = 20
    _BASE_DURATION_SECONDS = 30
    _GROWTH_RATE = 0.18

    def select_targets(self, profiles: list[EntityProfile], events_df: pd.DataFrame) -> list[EntityProfile]:
        eligible = [
            profile for profile in profiles if profile.entity_type == "user" and profile.has_history() and profile.normal_resources
        ]
        return self._sample_targets(eligible)

    def generate_incident(
        self, profile: EntityProfile, events_df: pd.DataFrame, incident_index: int
    ) -> list[InjectedEvent]:
        if events_df.empty:
            return []

        available_days = safe_local_day_range(events_df)

        session_count = max(
            self._MIN_SESSIONS, round(self._rng.randint(self._MIN_SESSIONS, self._MAX_SESSIONS) * self.config.intensity)
        )
        session_count = min(session_count, len(available_days))
        if session_count < 2:
            return []

        incident_days = sorted(self._rng.sample(available_days, k=session_count))
        resource = self._rng.choice(profile.normal_resources)
        device = profile.known_devices[0] if profile.known_devices else "unknown-device"
        auth_method = profile.authentication_methods[0] if profile.authentication_methods else "sso"
        source_ip = profile.known_source_ips[0] if profile.known_source_ips else "0.0.0.0"

        off_hours_candidates = [
            hour for hour in range(24) if not (profile.working_hours_start <= hour < profile.working_hours_end)
        ]
        off_hour = self._rng.choice(off_hours_candidates) if off_hours_candidates else profile.working_hours_start

        span_days = (incident_days[-1] - incident_days[0]).days
        metadata = self._make_metadata(
            confidence=self._rng.uniform(0.4, 0.7),
            description=(
                f"{profile.entity_id} repeatedly accessed {resource} during off-hours across "
                f"{session_count} sessions spanning {span_days} days, with session duration gradually "
                f"increasing — consistent with low-and-slow data exfiltration designed to stay below "
                f"per-session detection thresholds."
            ),
        )

        events: list[InjectedEvent] = []
        for day_index, day in enumerate(incident_days):
            timestamp = random_timestamp_at_hour(day, off_hour, profile.timezone, self._rng)
            duration = int(self._BASE_DURATION_SECONDS * (1 + self._GROWTH_RATE * day_index)) + self._rng.randint(-5, 5)
            duration = max(10, duration)

            events.append(
                InjectedEvent(
                    event_id=generate_attack_event_id(),
                    timestamp=timestamp,
                    entity_id=profile.entity_id,
                    entity_type=profile.entity_type,
                    source_ip=source_ip,
                    geo_location=profile.home_location,
                    resource_accessed=resource,
                    auth_method=auth_method,
                    session_duration=duration,
                    command_sequence=("access_resource", "export_data"),
                    device_fingerprint=device,
                    login_result="success",
                    risk_context=compute_attack_risk_context(
                        is_working_time=False,
                        is_remote=profile.is_remote,
                        is_known_device=True,
                        is_expected_resource=True,
                    ),
                    label="attack",
                    metadata=metadata,
                )
            )
        return events