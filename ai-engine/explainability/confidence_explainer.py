from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from explainability.evidence_aggregator import ExplainabilityEvidence


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ConfidenceBandConfig:
    """Configurable boundaries for translating Phase 5's continuous 0.0-1.0
    confidence into a Low/Medium/High band an analyst can triage against
    at a glance. Defaults are calibrated against the real confidence
    distribution from a full Phase 5 run (mean ~0.51, p90 ~0.77, max
    ~0.80): most events land in the 0.4-0.65 medium band, with a genuine
    high tier above it and a genuine low tier below it.
    """

    low_threshold: float = 0.40
    high_threshold: float = 0.65

    def __post_init__(self) -> None:
        if not 0.0 <= self.low_threshold < self.high_threshold <= 1.0:
            raise ValueError(
                f"ConfidenceBandConfig requires 0.0 <= low_threshold < high_threshold <= 1.0, "
                f"got low={self.low_threshold}, high={self.high_threshold}"
            )


@dataclass(frozen=True)
class ConfidenceExplanation:
    """Why Phase 5's confidence score landed where it did, decomposed into
    the same three signals ConfidenceEngine actually weighted — reconstructed
    here purely by reading already-persisted Phase 5 output columns
    (`confidence`, `score_<attack_type>`, `detection_anomaly_score`), never
    by recomputing confidence itself.
    """

    confidence: float
    level: ConfidenceLevel
    match_strength: float
    margin: float
    detection_strength: float
    narrative: str

    def to_dict(self) -> dict[str, object]:
        return {
            "confidence": self.confidence,
            "confidence_level": self.level.value,
            "match_strength": self.match_strength,
            "margin": self.margin,
            "detection_strength": self.detection_strength,
            "confidence_narrative": self.narrative,
        }


class ConfidenceExplainer:
    """Explains a Phase 5 confidence score in analyst-facing terms."""

    def __init__(self, config: ConfidenceBandConfig | None = None) -> None:
        self.config = config or ConfidenceBandConfig()

    def explain(self, evidence: ExplainabilityEvidence) -> ConfidenceExplanation:
        c = evidence.classification
        confidence = c.confidence

        match_strength = c.attack_type_scores.get(c.attack_type, 0.0)
        ranked_scores = sorted(c.attack_type_scores.values(), reverse=True)
        second_best = ranked_scores[1] if len(ranked_scores) > 1 else 0.0
        margin = max(0.0, match_strength - second_best)
        detection_strength = evidence.detection.anomaly_score

        level = self._level_for(confidence)
        narrative = self._narrative(
            level=level,
            confidence=confidence,
            match_strength=match_strength,
            margin=margin,
            detection_strength=detection_strength,
            attack_type=c.display_name,
        )

        return ConfidenceExplanation(
            confidence=confidence,
            level=level,
            match_strength=round(match_strength, 4),
            margin=round(margin, 4),
            detection_strength=round(detection_strength, 4),
            narrative=narrative,
        )

    def _level_for(self, confidence: float) -> ConfidenceLevel:
        if confidence >= self.config.high_threshold:
            return ConfidenceLevel.HIGH
        if confidence >= self.config.low_threshold:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    def _narrative(
        self,
        *,
        level: ConfidenceLevel,
        confidence: float,
        match_strength: float,
        margin: float,
        detection_strength: float,
        attack_type: str,
    ) -> str:
        base = (
            f"Confidence is {level.value} ({confidence:.0%}), built from a {match_strength:.0%} indicator match "
            f"for '{attack_type}', a {margin:.0%} margin over the next-closest attack type, and a "
            f"{detection_strength:.0%} underlying detection anomaly score."
        )
        if level == ConfidenceLevel.HIGH:
            return base + " This is a decisive match with strong supporting evidence — treat this classification as reliable."
        if level == ConfidenceLevel.MEDIUM:
            return base + " The evidence points this way but is not overwhelming — corroborate with the listed evidence before acting."
        return base + " The evidence is weak or ambiguous — treat the attack type as a lead for investigation, not a conclusion."