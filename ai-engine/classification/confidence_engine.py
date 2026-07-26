from __future__ import annotations

import math
from dataclasses import dataclass

from classification.attack_classifier import ClassificationScores
from classification.attack_registry import AttackType
from classification.evidence_collector import EvidenceBundle
from detection.score_normalizer import clamp


@dataclass(frozen=True)
class ConfidenceEngineConfig:
    match_weight: float = 0.5
    margin_weight: float = 0.3
    detection_strength_weight: float = 0.2
    unknown_confidence_cap: float = 0.4

    def __post_init__(self) -> None:
        total = self.match_weight + self.margin_weight + self.detection_strength_weight
        if not math.isclose(total, 1.0, abs_tol=1e-6):
            raise ValueError(f"ConfidenceEngineConfig weights must sum to 1.0, got {total}")
        if not 0.0 <= self.unknown_confidence_cap <= 1.0:
            raise ValueError("unknown_confidence_cap must fall within [0.0, 1.0].")


class ConfidenceEngine:
    """Produces the required 0.0-1.0 confidence score for a chosen attack
    type, from three independent signals:

      - Match strength -> the winning attack type's own indicator score
        (how many of its defining checks fired).
      - Margin         -> how decisively it won over the runner-up. A
        score of 0.6 that beat every other type by a wide margin deserves
        more confidence than the same 0.6 in a near-four-way tie.
      - Detection strength -> Phase 4's own anomaly_score for this event.
        A classification built on a barely-anomalous event is inherently
        less certain than one built on a strongly anomalous one, even if
        the attack-type signature match itself looks identical.

    AttackType.UNKNOWN is capped separately: by definition nothing matched
    strongly, so its confidence should never look as certain as a real
    signature match, regardless of how the weighted formula alone would
    score it.
    """

    def __init__(self, config: ConfidenceEngineConfig | None = None) -> None:
        self.config = config or ConfidenceEngineConfig()

    def compute_confidence(
        self,
        *,
        scores: ClassificationScores,
        chosen: AttackType,
        evidence: EvidenceBundle,
    ) -> float:
        top_score = scores.scores.get(chosen, 0.0)
        ranked = sorted(scores.scores.values(), reverse=True)
        second_score = ranked[1] if len(ranked) > 1 else 0.0
        margin = clamp(top_score - second_score)
        detection_strength = clamp(evidence.anomaly_score)

        raw = (
            self.config.match_weight * top_score
            + self.config.margin_weight * margin
            + self.config.detection_strength_weight * detection_strength
        )
        confidence = clamp(raw)

        if chosen == AttackType.UNKNOWN:
            confidence = min(confidence, self.config.unknown_confidence_cap)

        return round(confidence, 4)