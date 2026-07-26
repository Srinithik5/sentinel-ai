from __future__ import annotations

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
from generators.organization import DEPARTMENT_RESOURCES
from schemas.enums import Department


class LateralMovementAttack(AttackModule):
    """A sequence of resource accesses that traverses outside the entity's
    own department, escalating toward IT/Security systems on later hops —
    unusual resource traversal + privilege escalation + new systems.
    """

    attack_type = "lateral_movement"
    mitre_tactic = "Lateral Movement"
    mitre_technique = "T1021 Remote Services"

    _MIN_HOPS = 3
    _MAX_HOPS = 7
    _ESCALATION_DEPARTMENTS = (Department.SECURITY, Department.IT)

    def select_targets(self, profiles: list[EntityProfile], events_df: pd.DataFrame) -> list[EntityProfile]:
        eligible = [
            profile for profile in profiles if profile.entity_type == "user" and profile.has_history() and profile.department
        ]
        return self._sample_targets(eligible)

    def generate_incident(
        self, profile: EntityProfile, events_df: pd.DataFrame, incident_index: int
    ) -> list[InjectedEvent]:
        entity_events = events_df[events_df["entity_id"] == profile.entity_id].sort_values("timestamp")
        if entity_events.empty or not profile.department:
            return []

        anchor_time = entity_events["timestamp"].iloc[-1]
        if anchor_time.tzinfo is None:
            anchor_time = anchor_time.tz_localize("UTC")
        anchor_time = anchor_time.to_pydatetime()

        other_departments = [department for department in DEPARTMENT_RESOURCES if department.value != profile.department]
        if not other_departments:
            return []

        hop_count = max(self._MIN_HOPS, round(self._rng.randint(self._MIN_HOPS, self._MAX_HOPS) * self.config.intensity))
        escalation_pool = [department for department in self._ESCALATION_DEPARTMENTS if department in other_departments]

        hop_departments = [self._rng.choice(other_departments) for _ in range(hop_count - 1)]
        hop_departments.append(self._rng.choice(escalation_pool) if escalation_pool else self._rng.choice(other_departments))

        device = profile.known_devices[0] if profile.known_devices else "unknown-device"
        source_ip = profile.known_source_ips[0] if profile.known_source_ips else "0.0.0.0"
        auth_method = profile.authentication_methods[0] if profile.authentication_methods else "sso"

        metadata = self._make_metadata(
            confidence=self._rng.uniform(0.6, 0.85),
            description=(
                f"{profile.entity_id} accessed {hop_count} resources outside its normal department "
                f"({profile.department}) in a short sequence, progressively reaching more sensitive "
                f"systems — consistent with an attacker pivoting through the network after initial "
                f"compromise."
            ),
        )

        boundary = dataset_end_boundary(events_df)

        events: list[InjectedEvent] = []
        cursor_time = anchor_time
        for department in hop_departments:
            cursor_time = cursor_time + timedelta(minutes=self._rng.uniform(4, 25))
            if cursor_time > boundary:
                # Later hops would extend past the dataset's declared date
                # range — stop here rather than generate an out-of-range
                # event; whatever hops already fit remain a valid incident.
                break
            resource = self._rng.choice(DEPARTMENT_RESOURCES[department].primary_resources)

            events.append(
                InjectedEvent(
                    event_id=generate_attack_event_id(),
                    timestamp=cursor_time,
                    entity_id=profile.entity_id,
                    entity_type=profile.entity_type,
                    source_ip=source_ip,
                    geo_location=profile.home_location,
                    resource_accessed=resource,
                    auth_method=auth_method,
                    session_duration=self._rng.randint(60, 600),
                    command_sequence=("access_resource", "enumerate_permissions"),
                    device_fingerprint=device,
                    login_result="success",
                    risk_context=compute_attack_risk_context(
                        is_working_time=is_within_working_hours(profile, cursor_time),
                        is_remote=profile.is_remote,
                        is_known_device=True,
                        is_expected_resource=False,
                    ),
                    label="attack",
                    metadata=metadata,
                )
            )
        return events