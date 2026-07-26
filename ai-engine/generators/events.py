from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np

from config.simulation_config import SimulationConfig
from generators.behavior import (
    compute_risk_context,
    determine_login_result,
    generate_command_sequence,
    sample_session_duration,
    select_device,
    select_resource,
)
from schemas.entity_schema import Entity
from schemas.enums import EventLabel
from schemas.event_schema import AccessEvent
from utils.identifiers import generate_event_id
from utils.network import REMOTE_NETWORK_CIDR, random_ip_in_cidr, stable_ip_for_entity
from utils.time_utils import random_business_timestamp, random_timestamp_at_hour

_PERIODIC_SCHEDULE_TYPES = ("periodic_edge", "periodic_iot")


def generate_events_for_entity(
    entity: Entity,
    days: list[date],
    scale_factor: float,
    config: SimulationConfig,
    rng: random.Random,
    np_rng: np.random.Generator,
) -> list[AccessEvent]:
    cidr = REMOTE_NETWORK_CIDR if entity.is_remote else entity.network_cidr
    primary_ip = stable_ip_for_entity(entity.entity_id, cidr)

    if entity.schedule_type in _PERIODIC_SCHEDULE_TYPES:
        return _generate_periodic_events(entity, days, scale_factor, config, rng, primary_ip)
    return _generate_stochastic_events(entity, days, scale_factor, config, rng, np_rng, primary_ip)


def _generate_stochastic_events(
    entity: Entity,
    days: list[date],
    scale_factor: float,
    config: SimulationConfig,
    rng: random.Random,
    np_rng: np.random.Generator,
    primary_ip: str,
) -> list[AccessEvent]:
    active_days = [day for day in days if day.weekday() in entity.working_hours.active_days]
    if not active_days:
        return []

    daily_mean = max(entity.normal_login_frequency * scale_factor, 0.01)
    hour_start = entity.working_hours.start_hour
    hour_end = entity.working_hours.end_hour
    off_hours_probability = min(0.15, config.noise_level * 0.15)
    tz = ZoneInfo(entity.timezone)

    events: list[AccessEvent] = []
    for day in active_days:
        event_count = int(np_rng.poisson(lam=daily_mean))
        for _ in range(event_count):
            if rng.random() < off_hours_probability:
                candidate_hours = [h for h in range(24) if not (hour_start <= h < hour_end)]
                hour = rng.choice(candidate_hours) if candidate_hours else rng.randint(0, 23)
                timestamp_utc = random_timestamp_at_hour(day, hour, entity.timezone, rng)
            else:
                timestamp_utc = random_business_timestamp(day, hour_start, hour_end, entity.timezone, rng)

            local_dt = timestamp_utc.astimezone(tz)
            is_working_time = entity.working_hours.is_working_time(local_dt.hour, local_dt.weekday())

            events.append(
                _build_event(entity, timestamp_utc, is_working_time, rng, config.noise_level, primary_ip)
            )

    return events


def _generate_periodic_events(
    entity: Entity,
    days: list[date],
    scale_factor: float,
    config: SimulationConfig,
    rng: random.Random,
    primary_ip: str,
) -> list[AccessEvent]:
    effective_frequency = entity.normal_login_frequency * scale_factor
    if effective_frequency <= 0:
        return []
    interval_seconds = max(30.0, 86_400.0 / effective_frequency)

    cursor = datetime.combine(days[0], time.min, tzinfo=timezone.utc)
    end = datetime.combine(days[-1], time.max, tzinfo=timezone.utc)

    events: list[AccessEvent] = []
    while cursor <= end:
        jitter_seconds = rng.uniform(-0.1, 0.1) * interval_seconds
        event_time = cursor + timedelta(seconds=jitter_seconds)
        # Always True: edge/IoT devices are configured for round-the-clock
        # activity (hours 0-24, all 7 days), so every generated timestamp
        # falls within their working-hours window by construction.
        events.append(_build_event(entity, event_time, True, rng, config.noise_level, primary_ip))
        cursor += timedelta(seconds=interval_seconds)

    return events


def _build_event(
    entity: Entity,
    timestamp: datetime,
    is_working_time: bool,
    rng: random.Random,
    noise_level: float,
    primary_ip: str,
) -> AccessEvent:
    resource = select_resource(entity, rng)
    device = select_device(entity, rng)
    auth_method = rng.choice(entity.authentication_methods)
    session_duration = sample_session_duration(entity.entity_type, rng)
    command_sequence = generate_command_sequence(entity, resource, rng)
    login_result = determine_login_result(rng, noise_level)
    risk_context = compute_risk_context(entity, is_working_time, resource, device)

    alternate_ip_chance = min(0.2, noise_level * 0.5)
    if rng.random() < alternate_ip_chance:
        cidr = REMOTE_NETWORK_CIDR if entity.is_remote else entity.network_cidr
        source_ip = random_ip_in_cidr(cidr, rng)
    else:
        source_ip = primary_ip

    return AccessEvent(
        event_id=generate_event_id(),
        timestamp=timestamp,
        entity_id=entity.entity_id,
        entity_type=entity.entity_type,
        source_ip=source_ip,
        geo_location=entity.home_location,
        resource_accessed=resource,
        auth_method=auth_method,
        session_duration=session_duration,
        command_sequence=command_sequence,
        device_fingerprint=device,
        login_result=login_result,
        risk_context=risk_context,
        label=EventLabel.NORMAL,
    )