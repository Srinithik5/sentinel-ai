from __future__ import annotations

import pandas as pd

from attacks.base import InjectedEvent

GROUND_TRUTH_COLUMNS: tuple[str, ...] = (
    "event_id",
    "entity_id",
    "is_attack",
    "attack_id",
    "attack_type",
    "severity",
    "mitre_tactic",
    "mitre_technique",
    "confidence",
)


def build_ground_truth(events_df: pd.DataFrame, injected_events: list[InjectedEvent]) -> pd.DataFrame:
    """Authoritative label table covering every event (original + injected).

    This is fully separate from the merged dataset's own `label` column —
    the original events' labels are never touched; this table is the one
    downstream training should treat as ground truth.
    """

    normal_rows = [
        {
            "event_id": event_id,
            "entity_id": entity_id,
            "is_attack": False,
            "attack_id": None,
            "attack_type": None,
            "severity": None,
            "mitre_tactic": None,
            "mitre_technique": None,
            "confidence": None,
        }
        for event_id, entity_id in zip(events_df["event_id"], events_df["entity_id"])
    ]

    attack_rows = [
        {
            "event_id": event.event_id,
            "entity_id": event.entity_id,
            "is_attack": True,
            "attack_id": event.metadata.attack_id,
            "attack_type": event.metadata.attack_type,
            "severity": event.metadata.severity,
            "mitre_tactic": event.metadata.mitre_tactic,
            "mitre_technique": event.metadata.mitre_technique,
            "confidence": event.metadata.confidence,
        }
        for event in injected_events
    ]

    return pd.DataFrame(normal_rows + attack_rows, columns=list(GROUND_TRUTH_COLUMNS))