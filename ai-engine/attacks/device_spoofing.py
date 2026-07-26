from __future__ import annotations

import random
from datetime import timedelta

import pandas as pd

from attacks.base import (
    AttackModule,
    InjectedEvent,
    compute_attack_risk_context,
    dataset_end_boundary,
    generate_attack_event_id,
    is_within_working_hours,
)
from attacks.dataset_loader import EntityProfile
from utils.network import generate_device_fingerprint

_OS_OPTIONS: tuple[str, ...] = (
    "Windows 11",
    "Windows 10",
    "macOS 14",
    "macOS 13",
    "Ubuntu 22.04",
    "Android 14",
    "iOS 17",
)


def _random_mac(rng: random.Random) -> str:
    return ":".join(f"{rng.randint(0, 255):02x}" for _ in range(6))


class DeviceSpoofingAttack(AttackModule):
    """A session presenting a device fingerprint, OS, and MAC inconsistent
    with the entity's previously observed device — the same logical
    account, a different piece of hardware claiming to be trusted.
    """

    attack_type = "device_spoofing"
    mitre_tactic = "Defense Evasion"
    mitre_technique = "T1036 Masquerading"

    def select_targets(self, profiles: list[EntityProfile], events_df: pd.DataFrame) -> list[EntityProfile]:
        eligible = [profile for profile in profiles if profile.has_history()]
        return self._sample_targets(eligible)

    def generate_incident(
        self, profile: EntityProfile, events_df: pd.DataFrame, incident_index: int
    ) -> list[InjectedEvent]:
        entity_events = events_df[events_df["entity_id"] == profile.entity_id].sort_values("timestamp")
        if entity_events.empty:
            return []

        last_event_time = entity_events["timestamp"].iloc[-1]
        if last_event_time.tzinfo is None:
            last_event_time = last_event_time.tz_localize("UTC")
        last_event_time = last_event_time.to_pydatetime()

        headroom_minutes = (dataset_end_boundary(events_df) - last_event_time).total_seconds() / 60
        if headroom_minutes < 10.0:
            return []  # entity's last event is too close to the dataset boundary to fit a follow-up event

        anchor_time = last_event_time + timedelta(minutes=self._rng.uniform(10, min(240, headroom_minutes)))

        known_device = profile.known_devices[0]
        spoofed_fingerprint = generate_device_fingerprint(f"spoofed-{profile.entity_id}-{incident_index}")
        spoofed_os, baseline_os = self._rng.sample(list(_OS_OPTIONS), k=2)
        spoofed_mac = _random_mac(self._rng)

        resource = profile.normal_resources[0] if profile.normal_resources else "Authentication Gateway"
        auth_method = profile.authentication_methods[0] if profile.authentication_methods else "sso"
        source_ip = profile.known_source_ips[0] if profile.known_source_ips else "0.0.0.0"

        metadata = self._make_metadata(
            confidence=self._rng.uniform(0.55, 0.8),
            description=(
                f"A session for {profile.entity_id} presented device fingerprint "
                f"{spoofed_fingerprint[:12]}... with OS signature '{spoofed_os}', inconsistent with the "
                f"previously observed device (fingerprint {known_device[:12]}..., OS '{baseline_os}') — "
                f"consistent with device identity spoofing."
            ),
        )

        event = InjectedEvent(
            event_id=generate_attack_event_id(),
            timestamp=anchor_time,
            entity_id=profile.entity_id,
            entity_type=profile.entity_type,
            source_ip=source_ip,
            geo_location=profile.home_location,
            resource_accessed=resource,
            auth_method=auth_method,
            session_duration=self._rng.randint(60, 400),
            command_sequence=("login", "access_resource"),
            device_fingerprint=spoofed_fingerprint,
            login_result="success",
            risk_context=compute_attack_risk_context(
                is_working_time=is_within_working_hours(profile, anchor_time),
                is_remote=profile.is_remote,
                is_known_device=False,
                is_expected_resource=resource in profile.normal_resources,
            ),
            label="attack",
            metadata=metadata,
            device_os=spoofed_os,
            device_mac=spoofed_mac,
        )
        return [event]