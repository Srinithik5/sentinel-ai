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
from generators.organization import DEPARTMENT_RESOURCES
from utils.time_utils import random_business_timestamp


class InsiderDriftAttack(AttackModule):
    """The entity's accessed-resource set slowly expands beyond its normal
    baseline over the dataset's whole time span. Every individual session
    stays plausible (normal hours, normal device, normal auth) — only the
    longitudinal trend reveals the drift, making this the hardest attack
    type in the set to catch from any single event.
    """

    attack_type = "insider_drift"
    mitre_tactic = "Privilege Escalation"
    mitre_technique = "T1078 Valid Accounts"

    _CHECKPOINT_COUNT = 5
    _EVENTS_PER_CHECKPOINT = 3

    def select_targets(self, profiles: list[EntityProfile], events_df: pd.DataFrame) -> list[EntityProfile]:
        eligible = [
            profile for profile in profiles if profile.entity_type == "user" and profile.has_history() and profile.department
        ]
        return self._sample_targets(eligible)

    def generate_incident(
        self, profile: EntityProfile, events_df: pd.DataFrame, incident_index: int
    ) -> list[InjectedEvent]:
        if events_df.empty or not profile.department:
            return []

        days = safe_local_day_range(events_df)
        if len(days) < self._CHECKPOINT_COUNT:
            return []

        checkpoint_days = sorted(days[index * len(days) // self._CHECKPOINT_COUNT] for index in range(self._CHECKPOINT_COUNT))

        other_departments = [department for department in DEPARTMENT_RESOURCES if department.value != profile.department]
        expanding_resources: list[str] = list(profile.normal_resources) or ["General Access Portal"]
        device = profile.known_devices[0] if profile.known_devices else "unknown-device"
        auth_method = profile.authentication_methods[0] if profile.authentication_methods else "sso"
        source_ip = profile.known_source_ips[0] if profile.known_source_ips else "0.0.0.0"

        metadata = self._make_metadata(
            confidence=self._rng.uniform(0.3, 0.6),
            description=(
                f"{profile.entity_id}'s accessed resource set gradually expanded beyond its normal "
                f"baseline ({', '.join(profile.normal_resources) or 'none'}) over the observed period, "
                f"with each individual session remaining plausible — consistent with slow, creeping "
                f"scope drift rather than a single detectable event."
            ),
        )

        events: list[InjectedEvent] = []
        for checkpoint_index, day in enumerate(checkpoint_days):
            if checkpoint_index > 0 and other_departments:
                new_department = self._rng.choice(other_departments)
                other_departments.remove(new_department)
                expanding_resources.append(self._rng.choice(DEPARTMENT_RESOURCES[new_department].primary_resources))

            for _ in range(self._EVENTS_PER_CHECKPOINT):
                timestamp = random_business_timestamp(
                    day, profile.working_hours_start, profile.working_hours_end, profile.timezone, self._rng
                )
                resource = self._rng.choice(expanding_resources)

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
                        session_duration=self._rng.randint(60, 500),
                        command_sequence=("access_resource",),
                        device_fingerprint=device,
                        login_result="success",
                        risk_context=compute_attack_risk_context(
                            is_working_time=True,
                            is_remote=profile.is_remote,
                            is_known_device=True,
                            is_expected_resource=resource in profile.normal_resources,
                        ),
                        label="attack",
                        metadata=metadata,
                    )
                )
        return events