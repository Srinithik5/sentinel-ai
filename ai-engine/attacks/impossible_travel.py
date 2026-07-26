from __future__ import annotations

import math
from datetime import timedelta

import pandas as pd

from attacks.base import (
    ATTACKER_NETWORK_CIDR,
    AttackModule,
    InjectedEvent,
    compute_attack_risk_context,
    dataset_end_boundary,
    generate_attack_event_id,
    is_within_working_hours,
)
from attacks.dataset_loader import EntityProfile
from utils.network import generate_device_fingerprint, random_ip_in_cidr

# Approximate coordinates for Phase 2's six offices — kept local to this
# module since utils/network.py (locked) doesn't carry lat/lon.
_OFFICE_COORDINATES: dict[str, tuple[float, float]] = {
    "New York, USA": (40.7128, -74.0060),
    "London, United Kingdom": (51.5074, -0.1278),
    "Bangalore, India": (12.9716, 77.5946),
    "Singapore, Singapore": (1.3521, 103.8198),
    "Berlin, Germany": (52.5200, 13.4050),
    "Sydney, Australia": (-33.8688, 151.2093),
}

_EARTH_RADIUS_KM = 6371.0
_MAX_FEASIBLE_SPEED_KMH = 1000.0  # comfortably above commercial flight cruise speed (~900 km/h)


def _haversine_km(coord_a: tuple[float, float], coord_b: tuple[float, float]) -> float:
    lat1, lon1 = math.radians(coord_a[0]), math.radians(coord_a[1])
    lat2, lon2 = math.radians(coord_b[0]), math.radians(coord_b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return _EARTH_RADIUS_KM * 2 * math.asin(math.sqrt(a))


class ImpossibleTravelAttack(AttackModule):
    """A login from a geographically distant location too soon after the
    entity's own last known login for the implied travel speed to be
    physically feasible.
    """

    attack_type = "impossible_travel"
    mitre_tactic = "Initial Access"
    mitre_technique = "T1078 Valid Accounts"

    def select_targets(self, profiles: list[EntityProfile], events_df: pd.DataFrame) -> list[EntityProfile]:
        eligible = [
            profile
            for profile in profiles
            if profile.entity_type == "user" and profile.has_history() and profile.home_location in _OFFICE_COORDINATES
        ]
        return self._sample_targets(eligible)

    def generate_incident(
        self, profile: EntityProfile, events_df: pd.DataFrame, incident_index: int
    ) -> list[InjectedEvent]:
        entity_events = events_df[events_df["entity_id"] == profile.entity_id].sort_values("timestamp")
        if entity_events.empty:
            return []

        baseline_time = entity_events["timestamp"].iloc[-1]
        if baseline_time.tzinfo is None:
            baseline_time = baseline_time.tz_localize("UTC")
        baseline_time = baseline_time.to_pydatetime()

        candidate_locations = [loc for loc in _OFFICE_COORDINATES if loc != profile.home_location]
        if not candidate_locations:
            return []
        destination = self._rng.choice(candidate_locations)

        headroom_minutes = (dataset_end_boundary(events_df) - baseline_time).total_seconds() / 60
        if headroom_minutes < 5.0:
            return []  # entity's last event is too close to the dataset boundary to fit a follow-up event

        distance_km = _haversine_km(_OFFICE_COORDINATES[profile.home_location], _OFFICE_COORDINATES[destination])
        min_feasible_minutes = (distance_km / _MAX_FEASIBLE_SPEED_KMH) * 60
        upper_bound_minutes = min(max(10.0, min_feasible_minutes * 0.3), headroom_minutes)
        delta_minutes = self._rng.uniform(5.0, upper_bound_minutes)
        implied_speed_kmh = distance_km / (delta_minutes / 60)

        new_timestamp = baseline_time + timedelta(minutes=delta_minutes)
        attacker_ip = random_ip_in_cidr(ATTACKER_NETWORK_CIDR, self._rng)
        device = generate_device_fingerprint(f"impossible-travel-{profile.entity_id}-{incident_index}")
        resource = profile.normal_resources[0] if profile.normal_resources else "Authentication Gateway"
        auth_method = profile.authentication_methods[0] if profile.authentication_methods else "sso"

        metadata = self._make_metadata(
            confidence=self._rng.uniform(0.8, 0.95),
            description=(
                f"Login from {destination} occurred {delta_minutes:.1f} minutes after a login from "
                f"{profile.home_location}, implying a travel speed of {implied_speed_kmh:,.0f} km/h — "
                f"far exceeding the maximum feasible travel speed of {_MAX_FEASIBLE_SPEED_KMH:.0f} km/h."
            ),
        )

        event = InjectedEvent(
            event_id=generate_attack_event_id(),
            timestamp=new_timestamp,
            entity_id=profile.entity_id,
            entity_type=profile.entity_type,
            source_ip=attacker_ip,
            geo_location=destination,
            resource_accessed=resource,
            auth_method=auth_method,
            session_duration=180,
            command_sequence=("login",),
            device_fingerprint=device,
            login_result="success",
            risk_context=compute_attack_risk_context(
                is_working_time=is_within_working_hours(profile, new_timestamp),
                is_remote=True,
                is_known_device=False,
                is_expected_resource=resource in profile.normal_resources,
            ),
            label="attack",
            metadata=metadata,
        )
        return [event]