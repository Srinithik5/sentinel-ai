from __future__ import annotations

from generators.organization import DEPARTMENT_RESOURCES

from features.entity_history import EntityHistoryTracker, EntityStaticProfile

# A simple, defensible sensitivity ordering used only to decide whether a
# resource access represents a jump to a MORE sensitive tier than the
# entity's own department — not a redefinition of Phase 2's org model.
_DEPARTMENT_SENSITIVITY_TIER: dict[str, int] = {
    "HR": 1,
    "Sales": 1,
    "Operations": 1,
    "Engineering": 2,
    "Finance": 2,
    "IT": 3,
    "Security": 3,
}

_RESOURCE_DEPARTMENT: dict[str, str] = {
    resource: department.value
    for department, profile in DEPARTMENT_RESOURCES.items()
    for resource in (*profile.primary_resources, *profile.secondary_resources)
}

_SENSITIVE_RESOURCES: frozenset[str] = frozenset(
    resource
    for department, profile in DEPARTMENT_RESOURCES.items()
    if department.value in ("Security", "Finance", "IT")
    for resource in profile.primary_resources
)


def extract_resource_features(
    resource_accessed: str,
    static: EntityStaticProfile | None,
    tracker: EntityHistoryTracker,
) -> dict[str, object]:
    resource_department = _RESOURCE_DEPARTMENT.get(resource_accessed)

    privilege_change_indicator = False
    if static is not None and static.department and resource_department and resource_department != static.department:
        own_tier = _DEPARTMENT_SENSITIVITY_TIER.get(static.department, 1)
        resource_tier = _DEPARTMENT_SENSITIVITY_TIER.get(resource_department, 1)
        privilege_change_indicator = resource_tier > own_tier

    return {
        "resource_novelty": tracker.is_resource_novel(resource_accessed),
        "resource_diversity": round(tracker.resource_diversity, 4),
        "privilege_change_indicator": privilege_change_indicator,
        "sensitive_resource_access": resource_accessed in _SENSITIVE_RESOURCES,
    }