from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from schemas.enums import AuthMethod, EntityType, EventLabel, LoginResult


@dataclass(frozen=True)
class AccessEvent:
    event_id: str
    timestamp: datetime
    entity_id: str
    entity_type: EntityType
    source_ip: str
    geo_location: str
    resource_accessed: str
    auth_method: AuthMethod
    session_duration: int
    command_sequence: tuple[str, ...]
    device_fingerprint: str
    login_result: LoginResult
    risk_context: str
    label: EventLabel

    def to_row(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "entity_id": self.entity_id,
            "entity_type": self.entity_type.value,
            "source_ip": self.source_ip,
            "geo_location": self.geo_location,
            "resource_accessed": self.resource_accessed,
            "auth_method": self.auth_method.value,
            "session_duration": self.session_duration,
            "command_sequence": "|".join(self.command_sequence),
            "device_fingerprint": self.device_fingerprint,
            "login_result": self.login_result.value,
            "risk_context": self.risk_context,
            "label": self.label.value,
        }


EVENT_COLUMNS: tuple[str, ...] = (
    "event_id",
    "timestamp",
    "entity_id",
    "entity_type",
    "source_ip",
    "geo_location",
    "resource_accessed",
    "auth_method",
    "session_duration",
    "command_sequence",
    "device_fingerprint",
    "login_result",
    "risk_context",
    "label",
)