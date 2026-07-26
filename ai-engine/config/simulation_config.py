from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

DEFAULT_TIMEZONE_DISTRIBUTION: dict[str, float] = {
    "America/New_York": 0.30,
    "Europe/London": 0.20,
    "Asia/Kolkata": 0.20,
    "Asia/Singapore": 0.15,
    "Europe/Berlin": 0.10,
    "Australia/Sydney": 0.05,
}


@dataclass(frozen=True)
class SimulationConfig:
    num_users: int = 2000
    num_service_accounts: int = 150
    num_edge_devices: int = 100
    num_iot_devices: int = 250

    start_date: date = field(default_factory=lambda: date.today() - timedelta(days=30))
    end_date: date = field(default_factory=date.today)

    num_events: int = 250_000

    noise_level: float = 0.08
    remote_work_percentage: float = 0.35

    timezone_distribution: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_TIMEZONE_DISTRIBUTION)
    )

    random_seed: int = 42

    output_dir: Path = field(default_factory=lambda: Path("data/generated"))

    def __post_init__(self) -> None:
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        if not 0.0 <= self.noise_level <= 1.0:
            raise ValueError("noise_level must be between 0.0 and 1.0")
        if not 0.0 <= self.remote_work_percentage <= 1.0:
            raise ValueError("remote_work_percentage must be between 0.0 and 1.0")
        weight_total = sum(self.timezone_distribution.values())
        if not math.isclose(weight_total, 1.0, abs_tol=1e-6):
            raise ValueError(f"timezone_distribution weights must sum to 1.0, got {weight_total}")
        if self.num_users < 1:
            raise ValueError("num_users must be at least 1")
        if self.num_events < 1:
            raise ValueError("num_events must be at least 1")

    @property
    def total_entities(self) -> int:
        return (
            self.num_users
            + self.num_service_accounts
            + self.num_edge_devices
            + self.num_iot_devices
        )

    @property
    def date_range_days(self) -> int:
        return (self.end_date - self.start_date).days