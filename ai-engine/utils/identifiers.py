from __future__ import annotations

import uuid


def generate_entity_id(prefix: str, sequence: int) -> str:
    return f"{prefix}-{sequence:06d}"


def generate_event_id() -> str:
    return f"evt-{uuid.uuid4().hex[:16]}"