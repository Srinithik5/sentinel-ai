from __future__ import annotations

import random
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

from config.simulation_config import SimulationConfig
from generators.entities import EntityFactory
from generators.events import generate_events_for_entity
from schemas.entity_schema import Entity
from schemas.event_schema import EVENT_COLUMNS
from utils.time_utils import date_range


@dataclass(frozen=True)
class SimulationResult:
    entities: list[Entity]
    entities_df: pd.DataFrame
    events_df: pd.DataFrame
    generation_seconds: float


def _entities_to_dataframe(entities: list[Entity]) -> pd.DataFrame:
    rows = [
        {
            "entity_id": entity.entity_id,
            "entity_type": entity.entity_type.value,
            "display_name": entity.display_name,
            "department": entity.department.value if entity.department else None,
            "role": entity.role.value if entity.role else None,
            "privilege_level": entity.privilege_level.value,
            "home_location": entity.home_location,
            "home_country": entity.home_country,
            "timezone": entity.timezone,
            "working_hours_start": entity.working_hours.start_hour,
            "working_hours_end": entity.working_hours.end_hour,
            "active_days": ",".join(str(day) for day in entity.working_hours.active_days),
            "normal_resources": "|".join(entity.normal_resources),
            "trusted_device_count": len(entity.trusted_devices),
            "authentication_methods": "|".join(method.value for method in entity.authentication_methods),
            "normal_login_frequency": entity.normal_login_frequency,
            "is_remote": entity.is_remote,
            "network_cidr": entity.network_cidr,
            "schedule_type": entity.schedule_type,
        }
        for entity in entities
    ]
    return pd.DataFrame(rows)


class EnterpriseSimulator:
    def __init__(self, config: SimulationConfig) -> None:
        self._config = config

    def run(self) -> SimulationResult:
        started_at = time.perf_counter()

        factory = EntityFactory(self._config)
        entities = factory.generate_all()

        days = date_range(self._config.start_date, self._config.end_date)

        raw_weights = np.array(
            [
                entity.normal_login_frequency
                * sum(1 for day in days if day.weekday() in entity.working_hours.active_days)
                for entity in entities
            ],
            dtype=np.float64,
        )
        total_raw = float(raw_weights.sum())
        scale_factor = self._config.num_events / total_raw if total_raw > 0 else 1.0

        rng = random.Random(self._config.random_seed)
        np_rng = np.random.default_rng(self._config.random_seed)

        all_events = []
        for entity in entities:
            all_events.extend(
                generate_events_for_entity(
                    entity=entity,
                    days=days,
                    scale_factor=scale_factor,
                    config=self._config,
                    rng=rng,
                    np_rng=np_rng,
                )
            )

        all_events.sort(key=lambda event: event.timestamp)

        events_df = pd.DataFrame([event.to_row() for event in all_events], columns=list(EVENT_COLUMNS))
        entities_df = _entities_to_dataframe(entities)

        generation_seconds = time.perf_counter() - started_at

        return SimulationResult(
            entities=entities,
            entities_df=entities_df,
            events_df=events_df,
            generation_seconds=generation_seconds,
        )