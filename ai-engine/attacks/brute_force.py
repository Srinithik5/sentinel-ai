from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from attacks.base import (
    ATTACKER_NETWORK_CIDR,
    AttackModule,
    InjectedEvent,
    compute_attack_risk_context,
    generate_attack_event_id,
    is_within_working_hours,
    pick_foreign_location,
)
from attacks.dataset_loader import EntityProfile
from utils.network import generate_device_fingerprint, random_ip_in_cidr
from utils.time_utils import date_range


class BruteForceAttack(AttackModule):
    """Rapid failed logins against one account from one unfamiliar IP.

    Characteristics: same IP, same account, high frequency, mostly failures
    with an optional final success representing a cracked weak password.
    """

    attack_type = "brute_force"
    mitre_tactic = "Credential Access"
    mitre_technique = "T1110 Brute Force"

    _MIN_ATTEMPTS = 15
    _MAX_ATTEMPTS = 50
    _SUCCESS_PROBABILITY = 0.3
    _MIN_GAP_SECONDS = 3
    _MAX_GAP_SECONDS = 20

    def select_targets(self, profiles: list[EntityProfile], events_df: pd.DataFrame) -> list[EntityProfile]:
        eligible = [profile for profile in profiles if profile.entity_type == "user" and profile.has_history()]
        return self._sample_targets(eligible)

    def generate_incident(
        self, profile: EntityProfile, events_df: pd.DataFrame, incident_index: int
    ) -> list[InjectedEvent]:
        entity_events = events_df[events_df["entity_id"] == profile.entity_id]
        if entity_events.empty:
            return []

        start_date = entity_events["timestamp"].min().date()
        end_date = entity_events["timestamp"].max().date()
        incident_day = self._rng.choice(date_range(start_date, end_date))

        attack_ip = random_ip_in_cidr(ATTACKER_NETWORK_CIDR, self._rng)
        attacker_device = generate_device_fingerprint(f"brute-force-{profile.entity_id}-{incident_index}")
        attacker_location = pick_foreign_location(profile.home_location, self._rng)

        attempt_count = max(
            self._MIN_ATTEMPTS, round(self._rng.randint(self._MIN_ATTEMPTS, self._MAX_ATTEMPTS) * self.config.intensity)
        )
        resource = profile.normal_resources[0] if profile.normal_resources else "Authentication Gateway"
        auth_method = profile.authentication_methods[0] if profile.authentication_methods else "password"
        include_success = self._rng.random() < self._SUCCESS_PROBABILITY

        metadata = self._make_metadata(
            confidence=self._rng.uniform(0.85, 0.98),
            description=(
                f"{attempt_count} rapid login attempts against {profile.entity_id} from a single "
                f"unfamiliar source IP ({attack_ip}) within a short window, consistent with an "
                f"automated credential brute-force attempt."
            ),
        )

        events: list[InjectedEvent] = []
        cursor_seconds = self._rng.randint(0, 86_399)
        for attempt in range(attempt_count):
            cursor_seconds = (cursor_seconds + self._rng.randint(self._MIN_GAP_SECONDS, self._MAX_GAP_SECONDS)) % 86_400
            timestamp = datetime.combine(incident_day, time.min, tzinfo=timezone.utc) + timedelta(seconds=cursor_seconds)

            is_last_attempt = attempt == attempt_count - 1
            login_result = "success" if (is_last_attempt and include_success) else "failure"

            events.append(
                InjectedEvent(
                    event_id=generate_attack_event_id(),
                    timestamp=timestamp,
                    entity_id=profile.entity_id,
                    entity_type=profile.entity_type,
                    source_ip=attack_ip,
                    geo_location=attacker_location,
                    resource_accessed=resource,
                    auth_method=auth_method,
                    session_duration=2 if login_result == "failure" else 180,
                    command_sequence=() if login_result == "failure" else ("login",),
                    device_fingerprint=attacker_device,
                    login_result=login_result,
                    risk_context=compute_attack_risk_context(
                        is_working_time=is_within_working_hours(profile, timestamp),
                        is_remote=True,
                        is_known_device=False,
                        is_expected_resource=resource in profile.normal_resources,
                    ),
                    label="attack",
                    metadata=metadata,
                )
            )
        return events