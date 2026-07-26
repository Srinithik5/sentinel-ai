from __future__ import annotations

import random

from generators.organization import DEPARTMENT_RESOURCES, GENERIC_COMMAND_POOL
from schemas.entity_schema import Entity
from schemas.enums import EntityType, LoginResult

# entity_type -> (lognormal mu, lognormal sigma, min_seconds, max_seconds)
_SESSION_DURATION_PARAMS: dict[EntityType, tuple[float, float, int, int]] = {
    EntityType.USER: (5.2, 0.6, 15, 7200),
    EntityType.SERVICE_ACCOUNT: (3.4, 0.5, 5, 900),
    EntityType.EDGE_DEVICE: (1.0, 0.4, 1, 30),
    EntityType.IOT_DEVICE: (0.7, 0.3, 1, 15),
}


def select_resource(entity: Entity, rng: random.Random) -> str:
    resources = entity.normal_resources
    if not resources:
        return "General Access Portal"
    if len(resources) == 1:
        return resources[0]
    primary_weight = 0.65
    remaining_weight = (1.0 - primary_weight) / (len(resources) - 1)
    weights = [primary_weight] + [remaining_weight] * (len(resources) - 1)
    return rng.choices(resources, weights=weights, k=1)[0]


def select_device(entity: Entity, rng: random.Random) -> str:
    devices = entity.trusted_devices
    if len(devices) == 1:
        return devices[0]
    primary_weight = 0.75
    remaining_weight = (1.0 - primary_weight) / (len(devices) - 1)
    weights = [primary_weight] + [remaining_weight] * (len(devices) - 1)
    return rng.choices(devices, weights=weights, k=1)[0]


def _command_pool_for(entity: Entity, resource: str) -> tuple[str, ...]:
    if entity.department is not None:
        profile = DEPARTMENT_RESOURCES.get(entity.department)
        if profile is not None and resource in profile.command_pool:
            return profile.command_pool[resource]
    return GENERIC_COMMAND_POOL


def generate_command_sequence(entity: Entity, resource: str, rng: random.Random) -> tuple[str, ...]:
    pool = _command_pool_for(entity, resource)
    length = rng.randint(1, min(5, len(pool)))
    return tuple(rng.choices(pool, k=length))


def sample_session_duration(entity_type: EntityType, rng: random.Random) -> int:
    mu, sigma, min_seconds, max_seconds = _SESSION_DURATION_PARAMS[entity_type]
    duration = rng.lognormvariate(mu, sigma)
    return int(min(max(duration, min_seconds), max_seconds))


def determine_login_result(rng: random.Random, noise_level: float) -> LoginResult:
    base_failure_rate = 0.015
    failure_rate = min(0.12, base_failure_rate + noise_level * 0.05)
    return LoginResult.FAILURE if rng.random() < failure_rate else LoginResult.SUCCESS


def compute_risk_context(
    entity: Entity,
    is_working_time: bool,
    resource: str,
    device_used: str,
) -> str:
    tags = [
        "in_hours" if is_working_time else "off_hours",
        "remote_location" if entity.is_remote else "home_location",
        "primary_device" if device_used == entity.trusted_devices[0] else "secondary_device",
        "expected_resource" if resource in entity.normal_resources else "unlisted_resource",
    ]
    return "|".join(tags)