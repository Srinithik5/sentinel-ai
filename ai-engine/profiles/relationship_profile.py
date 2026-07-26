from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class RelationshipProfile:
    sample_count: int
    associated_devices: tuple[str, ...]
    associated_resources: tuple[str, ...]
    associated_locations: tuple[str, ...]
    department: str | None
    department_common_resources: tuple[str, ...]
    resource_sharing_score: float

    def to_dict(self) -> dict[str, object]:
        return {
            "sample_count": self.sample_count,
            "associated_devices": list(self.associated_devices),
            "associated_resources": list(self.associated_resources),
            "associated_locations": list(self.associated_locations),
            "department": self.department,
            "department_common_resources": list(self.department_common_resources),
            "resource_sharing_score": self.resource_sharing_score,
        }

    @staticmethod
    def from_dict(data: dict[str, object]) -> "RelationshipProfile":
        return RelationshipProfile(
            sample_count=int(data["sample_count"]),
            associated_devices=tuple(data["associated_devices"]),
            associated_resources=tuple(data["associated_resources"]),
            associated_locations=tuple(data["associated_locations"]),
            department=data["department"],
            department_common_resources=tuple(data["department_common_resources"]),
            resource_sharing_score=float(data["resource_sharing_score"]),
        )


def build_department_resource_index(
    events_by_entity: dict[str, pd.DataFrame],
    departments_by_entity: dict[str, str | None],
    *,
    top_resource_count: int = 10,
) -> dict[str, tuple[str, ...]]:
    """Aggregates the most common resources per department across ALL
    entities once, so each entity's RelationshipProfile can compare itself
    to its peer group without recomputing this on every call.
    """
    department_resource_counts: dict[str, dict[str, int]] = {}
    for entity_id, events in events_by_entity.items():
        department = departments_by_entity.get(entity_id)
        if not department:
            continue
        counts = department_resource_counts.setdefault(department, {})
        for resource in events["resource_accessed"]:
            counts[str(resource)] = counts.get(str(resource), 0) + 1

    index: dict[str, tuple[str, ...]] = {}
    for department, counts in department_resource_counts.items():
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        index[department] = tuple(resource for resource, _count in ranked[:top_resource_count])
    return index


def build_relationship_profile(
    entity_events: pd.DataFrame,
    *,
    department: str | None,
    department_common_resources: tuple[str, ...],
) -> RelationshipProfile:
    sample_count = len(entity_events)
    if sample_count == 0:
        return RelationshipProfile(0, (), (), (), department, department_common_resources, 0.0)

    associated_devices = tuple(sorted(entity_events["device_fingerprint"].astype(str).unique()))
    associated_resources = tuple(sorted(entity_events["resource_accessed"].astype(str).unique()))
    associated_locations = tuple(sorted(entity_events["geo_location"].astype(str).unique()))

    if department_common_resources:
        own_set = set(associated_resources)
        peer_set = set(department_common_resources)
        union = own_set | peer_set
        resource_sharing_score = round(len(own_set & peer_set) / len(union), 4) if union else 0.0
    else:
        resource_sharing_score = 0.0

    return RelationshipProfile(
        sample_count=sample_count,
        associated_devices=associated_devices,
        associated_resources=associated_resources,
        associated_locations=associated_locations,
        department=department,
        department_common_resources=department_common_resources,
        resource_sharing_score=resource_sharing_score,
    )