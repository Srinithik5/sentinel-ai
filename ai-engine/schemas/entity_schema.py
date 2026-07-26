from __future__ import annotations

from dataclasses import dataclass

from schemas.enums import AuthMethod, Department, EntityType, PrivilegeLevel, Role


@dataclass(frozen=True)
class WorkingHours:
    start_hour: int
    end_hour: int
    active_days: tuple[int, ...]
    timezone: str

    def is_working_time(self, local_hour: int, local_weekday: int) -> bool:
        return local_weekday in self.active_days and self.start_hour <= local_hour < self.end_hour


@dataclass(frozen=True)
class Entity:
    entity_id: str
    entity_type: EntityType
    display_name: str
    department: Department | None
    role: Role | None
    privilege_level: PrivilegeLevel
    home_location: str
    home_country: str
    timezone: str
    working_hours: WorkingHours
    normal_resources: tuple[str, ...]
    trusted_devices: tuple[str, ...]
    authentication_methods: tuple[AuthMethod, ...]
    normal_login_frequency: float
    is_remote: bool
    network_cidr: str
    schedule_type: str