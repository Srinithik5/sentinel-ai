from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

import pandas as pd

from attacks.base import (
    ATTACKER_NETWORK_CIDR,
    AttackConfig,
    AttackMetadata,
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


class CredentialStuffingAttack(AttackModule):
    """One coordinated campaign against many accounts from a small shared
    pool of IPs, mostly failing (invalid leaked pairs) with a small
    percentage succeeding (valid leaked pairs).

    Unlike the per-entity attacks, this is a single incident spanning many
    entities, so campaign-level state (IP pool, shared attack_id, campaign
    day) is established once in select_targets() and reused for every
    targeted entity's events.
    """

    attack_type = "credential_stuffing"
    mitre_tactic = "Credential Access"
    mitre_technique = "T1110.004 Credential Stuffing"

    _MIN_TARGETS = 8
    _IP_POOL_SIZE = 3
    _SUCCESS_PROBABILITY = 0.06

    def __init__(self, config: AttackConfig) -> None:
        super().__init__(config)
        self._campaign_ip_pool: tuple[str, ...] = ()
        self._campaign_device_by_ip: dict[str, str] = {}
        self._campaign_day: date | None = None
        self._campaign_metadata: AttackMetadata | None = None

    def select_targets(self, profiles: list[EntityProfile], events_df: pd.DataFrame) -> list[EntityProfile]:
        eligible = [profile for profile in profiles if profile.entity_type == "user" and profile.has_history()]
        targets = self._sample_targets(eligible, minimum=self._MIN_TARGETS)
        if not targets or events_df.empty:
            return []

        self._campaign_ip_pool = tuple(
            random_ip_in_cidr(ATTACKER_NETWORK_CIDR, self._rng) for _ in range(self._IP_POOL_SIZE)
        )
        self._campaign_device_by_ip = {
            ip: generate_device_fingerprint(f"credential-stuffing-{ip}") for ip in self._campaign_ip_pool
        }
        start_date = events_df["timestamp"].min().date()
        end_date = events_df["timestamp"].max().date()
        self._campaign_day = self._rng.choice(date_range(start_date, end_date))
        self._campaign_metadata = self._make_metadata(
            confidence=self._rng.uniform(0.7, 0.9),
            description=(
                f"Login attempts against {len(targets)} accounts originated from a shared pool of "
                f"{len(self._campaign_ip_pool)} external IP addresses within a single day — "
                f"consistent with a credential-stuffing campaign using leaked credential pairs."
            ),
        )
        return targets

    def generate_incident(
        self, profile: EntityProfile, events_df: pd.DataFrame, incident_index: int
    ) -> list[InjectedEvent]:
        if self._campaign_day is None or self._campaign_metadata is None or not self._campaign_ip_pool:
            return []

        attempt_count = max(1, round(self._rng.randint(1, 3) * self.config.intensity))
        resource = profile.normal_resources[0] if profile.normal_resources else "Authentication Gateway"
        auth_method = profile.authentication_methods[0] if profile.authentication_methods else "password"
        attack_ip = self._rng.choice(self._campaign_ip_pool)
        device = self._campaign_device_by_ip[attack_ip]

        events: list[InjectedEvent] = []
        for _ in range(attempt_count):
            seconds_in_day = self._rng.randint(0, 86_399)
            timestamp = datetime.combine(self._campaign_day, time.min, tzinfo=timezone.utc) + timedelta(
                seconds=seconds_in_day
            )
            login_result = "success" if self._rng.random() < self._SUCCESS_PROBABILITY else "failure"

            events.append(
                InjectedEvent(
                    event_id=generate_attack_event_id(),
                    timestamp=timestamp,
                    entity_id=profile.entity_id,
                    entity_type=profile.entity_type,
                    source_ip=attack_ip,
                    geo_location=pick_foreign_location(profile.home_location, self._rng),
                    resource_accessed=resource,
                    auth_method=auth_method,
                    session_duration=2 if login_result == "failure" else 120,
                    command_sequence=() if login_result == "failure" else ("login",),
                    device_fingerprint=device,
                    login_result=login_result,
                    risk_context=compute_attack_risk_context(
                        is_working_time=is_within_working_hours(profile, timestamp),
                        is_remote=True,
                        is_known_device=False,
                        is_expected_resource=resource in profile.normal_resources,
                    ),
                    label="attack",
                    metadata=self._campaign_metadata,
                )
            )
        return events