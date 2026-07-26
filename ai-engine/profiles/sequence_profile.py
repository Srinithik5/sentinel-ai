from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SequenceProfile:
    sample_count: int
    command_transition_matrix: dict[str, dict[str, float]]
    resource_transition_matrix: dict[str, dict[str, float]]
    common_resource_sequences: tuple[tuple[str, ...], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "sample_count": self.sample_count,
            "command_transition_matrix": {key: dict(value) for key, value in self.command_transition_matrix.items()},
            "resource_transition_matrix": {key: dict(value) for key, value in self.resource_transition_matrix.items()},
            "common_resource_sequences": [list(sequence) for sequence in self.common_resource_sequences],
        }

    @staticmethod
    def from_dict(data: dict[str, object]) -> "SequenceProfile":
        return SequenceProfile(
            sample_count=int(data["sample_count"]),
            command_transition_matrix={
                key: dict(value) for key, value in data["command_transition_matrix"].items()
            },
            resource_transition_matrix={
                key: dict(value) for key, value in data["resource_transition_matrix"].items()
            },
            common_resource_sequences=tuple(tuple(sequence) for sequence in data["common_resource_sequences"]),
        )


def _parse_command_sequence(raw: object) -> tuple[str, ...]:
    if isinstance(raw, str) and raw:
        return tuple(raw.split("|"))
    return ()


def _build_transition_matrix(sequences: list[tuple[str, ...]]) -> dict[str, dict[str, float]]:
    counts: dict[str, dict[str, int]] = {}
    for sequence in sequences:
        for current_state, next_state in zip(sequence, sequence[1:]):
            state_counts = counts.setdefault(current_state, {})
            state_counts[next_state] = state_counts.get(next_state, 0) + 1

    matrix: dict[str, dict[str, float]] = {}
    for state, next_counts in counts.items():
        total = sum(next_counts.values())
        matrix[state] = {
            next_state: round(count / total, 4) for next_state, count in sorted(next_counts.items())
        }
    return matrix


def build_sequence_profile(entity_events_sorted: pd.DataFrame, *, top_sequence_count: int = 5) -> SequenceProfile:
    """Builds a SequenceProfile from an entity's normal events, which MUST
    already be sorted chronologically — unlike the statistical profile,
    order is the entire point here. Uses first-order Markov chains, an
    explainable representation where every entry is directly interpretable
    as "given X, probability of Y next".
    """
    sample_count = len(entity_events_sorted)
    if sample_count == 0:
        return SequenceProfile(0, {}, {}, ())

    command_sequences = [_parse_command_sequence(raw) for raw in entity_events_sorted["command_sequence"]]
    command_transition_matrix = _build_transition_matrix(command_sequences)

    resource_sequence = tuple(str(resource) for resource in entity_events_sorted["resource_accessed"])
    resource_transition_matrix = _build_transition_matrix([resource_sequence])

    trigram_counts: dict[tuple[str, ...], int] = {}
    for index in range(len(resource_sequence) - 2):
        trigram = resource_sequence[index : index + 3]
        trigram_counts[trigram] = trigram_counts.get(trigram, 0) + 1

    ranked_trigrams = sorted(trigram_counts.items(), key=lambda item: (-item[1], item[0]))
    common_resource_sequences = tuple(trigram for trigram, _count in ranked_trigrams[:top_sequence_count])

    return SequenceProfile(
        sample_count=sample_count,
        command_transition_matrix=command_transition_matrix,
        resource_transition_matrix=resource_transition_matrix,
        common_resource_sequences=common_resource_sequences,
    )