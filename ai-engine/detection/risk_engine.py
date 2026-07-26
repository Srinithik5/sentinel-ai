from __future__ import annotations

import math
from dataclasses import dataclass

from detection.profile_comparator import EventRecord
from detection.score_normalizer import clamp, scale_to_risk_score
from profiles.profile_manager import BehaviourProfile, WarmupStrategy, build_cold_start_status

_GEO_VELOCITY_IMPLAUSIBLE_KMH = 900.0
_BURST_ACCESS_THRESHOLD = 10.0
_CONSECUTIVE_FAILURES_THRESHOLD = 3


def compute_attack_indicator_score(event: EventRecord) -> float:
    """A generic, rule-based count of behavioral red flags already present
    in Phase 2C's own engineered features. This is NOT attack-type
    inference — it never looks at which attack (if any) an event resembles,
    only how many independent structural warning signs are present.
    """
    checks = (
        event.consecutive_failures >= _CONSECUTIVE_FAILURES_THRESHOLD,
        event.fingerprint_mismatch,
        event.os_novelty or event.mac_novelty,
        event.geo_velocity_kmh > _GEO_VELOCITY_IMPLAUSIBLE_KMH,
        event.burst_access_score >= _BURST_ACCESS_THRESHOLD,
    )
    return round(sum(checks) / len(checks), 4)


@dataclass(frozen=True)
class RiskAssessment:
    risk_score: float
    deviation_component: float
    indicator_component: float
    confidence_component: float
    trust_component: float
    cold_start_component: float
    historical_confidence: float
    entity_trust: float

    def to_dict(self) -> dict[str, object]:
        return {
            "risk_score": self.risk_score,
            "deviation_component": self.deviation_component,
            "indicator_component": self.indicator_component,
            "confidence_component": self.confidence_component,
            "trust_component": self.trust_component,
            "cold_start_component": self.cold_start_component,
            "historical_confidence": self.historical_confidence,
            "entity_trust": self.entity_trust,
        }


@dataclass(frozen=True)
class RiskEngineConfig:
    deviation_weight: float = 0.40
    indicator_weight: float = 0.25
    confidence_weight: float = 0.15
    trust_weight: float = 0.10
    cold_start_weight: float = 0.10
    insufficient_data_floor: float = 0.5
    warming_up_floor: float = 0.2
    established_floor: float = 0.0

    def __post_init__(self) -> None:
        total = (
            self.deviation_weight
            + self.indicator_weight
            + self.confidence_weight
            + self.trust_weight
            + self.cold_start_weight
        )
        if not math.isclose(total, 1.0, abs_tol=1e-6):
            raise ValueError(f"RiskEngineConfig weights must sum to 1.0, got {total}")


class RiskEngine:
    """Produces the required normalized 0-100 risk score, combining exactly
    the five factors the spec calls for, each as an independent additive
    component so that none of them can silently cancel another out:

      - Behaviour deviation   -> anomaly_score itself, taken at face value.
        It is not damped by how much history the entity has: the
        ProfileComparator already accounts for limited history by
        returning neutral (0.5) deviations when a dimension can't be
        meaningfully compared, so the deviation signal is trustworthy on
        its own.
      - Historical confidence -> a well-known entity's baseline is more
        reliable, so LOW confidence itself contributes risk (an event
        measured against a shaky baseline deserves more caution, not less).
      - Cold-start confidence -> a separate, categorical baseline-caution
        floor (insufficient_data / warming_up / established).
      - Entity trust          -> behavioral stability, from Phase 3's own
        drift_score alone (a consistently-behaving entity is more
        trustworthy) — deliberately independent of historical_confidence,
        since sample volume and behavioral consistency are different axes
        and conflating them was what previously let both factors
        double-suppress the score for any not-yet-established entity.
      - Attack indicators     -> a generic, non-attack-type-specific
        rule-based red-flag count
    """

    def __init__(self, config: RiskEngineConfig | None = None) -> None:
        self.config = config or RiskEngineConfig()

    def compute_risk(
        self,
        *,
        event: EventRecord,
        profile: BehaviourProfile | None,
        anomaly_score: float,
    ) -> RiskAssessment:
        cold_start = profile.cold_start if profile is not None else build_cold_start_status(0, confidence_saturation=50)
        drift_score = profile.drift.drift_score if profile is not None else 0.0

        historical_confidence = cold_start.confidence_score
        entity_trust = round(clamp(1.0 - drift_score), 4) if profile is not None else 0.0

        deviation_component = round(clamp(anomaly_score), 4)
        indicator_component = compute_attack_indicator_score(event)
        confidence_component = round(1.0 - historical_confidence, 4)
        trust_component = round(1.0 - entity_trust, 4)
        cold_start_component = self._cold_start_floor(cold_start.warmup_strategy)

        raw = (
            self.config.deviation_weight * deviation_component
            + self.config.indicator_weight * indicator_component
            + self.config.confidence_weight * confidence_component
            + self.config.trust_weight * trust_component
            + self.config.cold_start_weight * cold_start_component
        )

        return RiskAssessment(
            risk_score=scale_to_risk_score(raw),
            deviation_component=deviation_component,
            indicator_component=indicator_component,
            confidence_component=confidence_component,
            trust_component=trust_component,
            cold_start_component=cold_start_component,
            historical_confidence=historical_confidence,
            entity_trust=entity_trust,
        )

    def _cold_start_floor(self, warmup_strategy: WarmupStrategy) -> float:
        return {
            WarmupStrategy.INSUFFICIENT_DATA: self.config.insufficient_data_floor,
            WarmupStrategy.WARMING_UP: self.config.warming_up_floor,
            WarmupStrategy.ESTABLISHED: self.config.established_floor,
        }[warmup_strategy]