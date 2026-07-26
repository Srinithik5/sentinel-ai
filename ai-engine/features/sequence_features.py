from __future__ import annotations

import math
from collections import Counter
from datetime import datetime

from features.entity_history import EntityHistoryTracker


def _parse_command_sequence(raw: object) -> tuple[str, ...]:
    if isinstance(raw, str) and raw:
        return tuple(raw.split("|"))
    return ()


def _shannon_entropy(commands: tuple[str, ...]) -> float:
    if not commands:
        return 0.0
    counts = Counter(commands)
    total = len(commands)
    entropy = 0.0
    for count in counts.values():
        probability = count / total
        entropy -= probability * math.log2(probability)
    return entropy


def extract_sequence_features(
    command_sequence_raw: object,
    timestamp: datetime,
    tracker: EntityHistoryTracker,
) -> dict[str, object]:
    commands = _parse_command_sequence(command_sequence_raw)

    command_sequence_complexity = (len(set(commands)) / len(commands)) if commands else 0.0

    return {
        "command_sequence_complexity": round(command_sequence_complexity, 4),
        "session_entropy": round(_shannon_entropy(commands), 4),
        "burst_access_score": tracker.burst_access_score(timestamp),
        "behaviour_drift_score": round(tracker.behaviour_drift_score(), 4),
    }