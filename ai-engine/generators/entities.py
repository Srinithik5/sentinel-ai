from __future__ import annotations

import random

from faker import Faker

from config.simulation_config import SimulationConfig
from generators.organization import (
    DEPARTMENT_ACTIVE_DAYS,
    DEPARTMENT_HEADCOUNT_WEIGHTS,
    DEPARTMENT_RESOURCES,
    DEPARTMENT_WORKING_HOURS,
    EDGE_DEVICE_TYPES,
    IOT_DEVICE_TYPES,
    ROLE_DISTRIBUTION,
    ROLE_PRIVILEGE_MAP,
    SERVICE_ACCOUNT_TEMPLATES,
)
from schemas.entity_schema import Entity, WorkingHours
from schemas.enums import AuthMethod, Department, EntityType, PrivilegeLevel, Role
from utils.identifiers import generate_entity_id
from utils.network import OFFICES, Office, generate_device_fingerprint

_DEFAULT_ACTIVE_DAYS: tuple[int, ...] = (0, 1, 2, 3, 4)
_ALL_WEEK_DAYS: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)

_SERVICE_ACCOUNT_FREQUENCY: dict[str, float] = {
    "nightly": 1.0,
    "business_hours_bursts": 12.0,
    "continuous": 48.0,
}

_USER_LOGIN_FREQUENCY_BASE: dict[Role, float] = {
    Role.INTERN: 4.0,
    Role.EMPLOYEE: 6.0,
    Role.MANAGER: 8.0,
    Role.ADMINISTRATOR: 10.0,
}


class EntityFactory:
    def __init__(self, config: SimulationConfig) -> None:
        self._config = config
        self._rng = random.Random(config.random_seed)
        self._offices = self._select_offices()
        self._faker = Faker()
        Faker.seed(config.random_seed)

    def generate_all(self) -> list[Entity]:
        entities: list[Entity] = []
        entities.extend(self.generate_users())
        entities.extend(self.generate_service_accounts())
        entities.extend(self.generate_edge_devices())
        entities.extend(self.generate_iot_devices())
        return entities

    def generate_users(self) -> list[Entity]:
        entities: list[Entity] = []
        for sequence in range(1, self._config.num_users + 1):
            department = self._weighted_department()
            role = self._weighted_role(department)
            office = self._weighted_office()
            privilege = ROLE_PRIVILEGE_MAP[role]
            is_remote = self._rng.random() < self._config.remote_work_percentage

            entity_id = generate_entity_id("USR", sequence)
            device_count = self._rng.choice([1, 1, 2, 2, 3])
            trusted_devices = tuple(
                generate_device_fingerprint(f"{entity_id}-device-{index}") for index in range(device_count)
            )

            entities.append(
                Entity(
                    entity_id=entity_id,
                    entity_type=EntityType.USER,
                    display_name=self._faker.name(),
                    department=department,
                    role=role,
                    privilege_level=privilege,
                    home_location=f"{office.city}, {office.country}",
                    home_country=office.country,
                    timezone=office.timezone,
                    working_hours=self._build_working_hours(department, office.timezone),
                    normal_resources=self._select_resources(department, role),
                    trusted_devices=trusted_devices,
                    authentication_methods=self._select_auth_methods(privilege),
                    normal_login_frequency=self._user_login_frequency(role),
                    is_remote=is_remote,
                    network_cidr=office.network_cidr,
                    schedule_type="business_hours",
                )
            )
        return entities

    def generate_service_accounts(self) -> list[Entity]:
        entities: list[Entity] = []
        for sequence in range(1, self._config.num_service_accounts + 1):
            template = SERVICE_ACCOUNT_TEMPLATES[(sequence - 1) % len(SERVICE_ACCOUNT_TEMPLATES)]
            office = self._weighted_office()
            entity_id = generate_entity_id("SVC", sequence)
            fingerprint = generate_device_fingerprint(f"{entity_id}-host")

            entities.append(
                Entity(
                    entity_id=entity_id,
                    entity_type=EntityType.SERVICE_ACCOUNT,
                    display_name=f"{template.purpose} [{entity_id}]",
                    department=template.department,
                    role=Role.SERVICE_ACCOUNT,
                    privilege_level=PrivilegeLevel.ELEVATED,
                    home_location=f"{office.city}, {office.country}",
                    home_country=office.country,
                    timezone=office.timezone,
                    working_hours=WorkingHours(
                        start_hour=0, end_hour=24, active_days=_ALL_WEEK_DAYS, timezone=office.timezone
                    ),
                    normal_resources=(template.resource,),
                    trusted_devices=(fingerprint,),
                    authentication_methods=(AuthMethod.API_KEY, AuthMethod.CERTIFICATE),
                    normal_login_frequency=_SERVICE_ACCOUNT_FREQUENCY[template.schedule],
                    is_remote=False,
                    network_cidr=office.network_cidr,
                    schedule_type=template.schedule,
                )
            )
        return entities

    def generate_edge_devices(self) -> list[Entity]:
        entities: list[Entity] = []
        for sequence in range(1, self._config.num_edge_devices + 1):
            device_type = EDGE_DEVICE_TYPES[(sequence - 1) % len(EDGE_DEVICE_TYPES)]
            office = self._weighted_office()
            entity_id = generate_entity_id("EDG", sequence)
            fingerprint = generate_device_fingerprint(f"{entity_id}-hw")

            entities.append(
                Entity(
                    entity_id=entity_id,
                    entity_type=EntityType.EDGE_DEVICE,
                    display_name=f"{device_type} [{entity_id}]",
                    department=Department.OPERATIONS,
                    role=None,
                    privilege_level=PrivilegeLevel.STANDARD,
                    home_location=f"{office.city}, {office.country}",
                    home_country=office.country,
                    timezone=office.timezone,
                    working_hours=WorkingHours(
                        start_hour=0, end_hour=24, active_days=_ALL_WEEK_DAYS, timezone=office.timezone
                    ),
                    normal_resources=("Building Automation Controller",),
                    trusted_devices=(fingerprint,),
                    authentication_methods=(AuthMethod.CERTIFICATE,),
                    normal_login_frequency=48.0,
                    is_remote=False,
                    network_cidr=office.network_cidr,
                    schedule_type="periodic_edge",
                )
            )
        return entities

    def generate_iot_devices(self) -> list[Entity]:
        entities: list[Entity] = []
        for sequence in range(1, self._config.num_iot_devices + 1):
            device_type = IOT_DEVICE_TYPES[(sequence - 1) % len(IOT_DEVICE_TYPES)]
            office = self._weighted_office()
            entity_id = generate_entity_id("IOT", sequence)
            fingerprint = generate_device_fingerprint(f"{entity_id}-hw")

            entities.append(
                Entity(
                    entity_id=entity_id,
                    entity_type=EntityType.IOT_DEVICE,
                    display_name=f"{device_type} [{entity_id}]",
                    department=Department.OPERATIONS,
                    role=None,
                    privilege_level=PrivilegeLevel.LOW,
                    home_location=f"{office.city}, {office.country}",
                    home_country=office.country,
                    timezone=office.timezone,
                    working_hours=WorkingHours(
                        start_hour=0, end_hour=24, active_days=_ALL_WEEK_DAYS, timezone=office.timezone
                    ),
                    normal_resources=("SCADA Historian",),
                    trusted_devices=(fingerprint,),
                    authentication_methods=(AuthMethod.API_KEY,),
                    normal_login_frequency=288.0,
                    is_remote=False,
                    network_cidr=office.network_cidr,
                    schedule_type="periodic_iot",
                )
            )
        return entities

    def _select_offices(self) -> list[Office]:
        selected = [office for office in OFFICES if office.timezone in self._config.timezone_distribution]
        if not selected:
            raise ValueError("No configured offices match the timezone_distribution")
        return selected

    def _weighted_office(self) -> Office:
        weights = [self._config.timezone_distribution[office.timezone] for office in self._offices]
        return self._rng.choices(self._offices, weights=weights, k=1)[0]

    def _weighted_department(self) -> Department:
        departments = list(DEPARTMENT_HEADCOUNT_WEIGHTS.keys())
        weights = list(DEPARTMENT_HEADCOUNT_WEIGHTS.values())
        return self._rng.choices(departments, weights=weights, k=1)[0]

    def _weighted_role(self, department: Department) -> Role:
        role_weights = ROLE_DISTRIBUTION[department]
        roles = list(role_weights.keys())
        weights = list(role_weights.values())
        return self._rng.choices(roles, weights=weights, k=1)[0]

    def _build_working_hours(self, department: Department, timezone: str) -> WorkingHours:
        start_hour, end_hour = DEPARTMENT_WORKING_HOURS[department]
        active_days = DEPARTMENT_ACTIVE_DAYS.get(department, _DEFAULT_ACTIVE_DAYS)
        return WorkingHours(start_hour=start_hour, end_hour=end_hour, active_days=active_days, timezone=timezone)

    def _select_resources(self, department: Department, role: Role) -> tuple[str, ...]:
        profile = DEPARTMENT_RESOURCES[department]
        resources = list(profile.primary_resources)
        if role in (Role.MANAGER, Role.ADMINISTRATOR) and profile.secondary_resources:
            resources.append(self._rng.choice(profile.secondary_resources))
        return tuple(resources)

    def _select_auth_methods(self, privilege: PrivilegeLevel) -> tuple[AuthMethod, ...]:
        if privilege in (PrivilegeLevel.ADMIN, PrivilegeLevel.ELEVATED):
            return (AuthMethod.SSO, AuthMethod.MFA)
        return (AuthMethod.SSO,)

    def _user_login_frequency(self, role: Role) -> float:
        base = _USER_LOGIN_FREQUENCY_BASE.get(role, 6.0)
        jitter = self._rng.uniform(-1.0, 1.0)
        return max(1.0, base + jitter)