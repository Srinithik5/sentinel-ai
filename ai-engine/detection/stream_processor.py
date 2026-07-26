from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from detection.detection_engine import DetectionEngine, DetectionResult
    from detection.profile_comparator import EventRecord


class StreamProcessor:
    """Feeds events one at a time into a DetectionEngine, maintaining the
    minimal per-entity state (last accessed resource) needed for
    sequence-aware comparison.

    `process_event` is the only real unit of work — it is what a live
    stream would call once per arriving event. `process_batch` is a thin
    convenience wrapper around it, not a separate code path: replaying a
    historical file and consuming a live feed run through identical logic.
    """

    def __init__(self, engine: "DetectionEngine") -> None:
        self.engine = engine
        self._last_resource_by_entity: dict[str, str] = {}

    def process_event(self, event: "EventRecord") -> "DetectionResult":
        previous_resource = self._last_resource_by_entity.get(event.entity_id)
        result = self.engine.detect(event, previous_resource=previous_resource)
        self._last_resource_by_entity[event.entity_id] = event.resource_accessed
        return result

    def process_batch(self, events: list["EventRecord"]) -> list["DetectionResult"]:
        return [self.process_event(event) for event in events]

    def reset(self) -> None:
        """Clears per-entity sequence state — e.g. when starting a fresh
        replay rather than continuing an ongoing stream.
        """
        self._last_resource_by_entity.clear()