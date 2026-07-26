from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from classification.attack_registry import KNOWN_ATTACK_TYPES, AttackType
from classification.evidence_collector import EvidenceBundle

# Kept numerically identical to the thresholds detection.risk_engine already
# established for the same underlying features, so a "bursty" or
# "implausible" reading means the same thing in both phases.
_BURST_ACCESS_THRESHOLD = 10.0
_GEO_VELOCITY_IMPLAUSIBLE_KMH = 900.0
_CONSECUTIVE_FAILURES_THRESHOLD = 3

# Phase 3's own drift-significance threshold (profiles/drift_profile.py),
# reused here rather than redefined so "elevated drift" means one thing
# across the whole project.
_DRIFT_SIGNIFICANCE_THRESHOLD = 0.35

# The Phase 4 deviation dimension each attack type is most directly
# evidenced by. Used only to break ties between attack types that scored
# identically on indicator-check count (see ClassificationEngine._select) —
# comparing the continuous deviation on each type's own primary dimension is
# a meaningful tie-break, unlike falling back to alphabetical order.
PRIMARY_DIMENSION: dict[AttackType, str] = {
    AttackType.BRUTE_FORCE: "authentication",
    AttackType.CREDENTIAL_STUFFING: "authentication",
    AttackType.IMPOSSIBLE_TRAVEL: "geographic",
    AttackType.DEVICE_SPOOFING: "device",
    AttackType.LATERAL_MOVEMENT: "resource",
    AttackType.LOW_AND_SLOW_EXFILTRATION: "session",
    AttackType.INSIDER_DRIFT: "resource",
}

_Check = tuple[bool, str]


def _score(checks: tuple[_Check, ...]) -> tuple[float, tuple[str, ...]]:
    matched = tuple(reason for is_true, reason in checks if is_true)
    return round(len(matched) / len(checks), 4), matched


@dataclass(frozen=True)
class ClassificationScores:
    """The output of one classification pass: a 0.0-1.0 match score per
    known attack type, plus the specific evidence strings that fired for
    each — the raw material ConfidenceEngine and ClassificationEngine
    consume to pick a winner and explain it.
    """

    scores: dict[AttackType, float]
    matched_indicators: dict[AttackType, tuple[str, ...]]


class ClassificationStrategy(ABC):
    """A pluggable method for turning one EvidenceBundle into per-attack-type
    match scores. New strategies (e.g. a trained multi-class model) plug in
    by implementing this interface — AttackClassifier and everything
    upstream of it never needs to change.
    """

    name: str

    @abstractmethod
    def classify(self, evidence: EvidenceBundle) -> ClassificationScores:
        """Returns a match score in [0.0, 1.0] for every known attack type."""


class RuleBasedClassificationStrategy(ClassificationStrategy):
    """Scores every attack type as the fraction of its defining indicator
    checks that fire for this event — the same "count matched checks /
    total checks" shape Phase 4's risk_engine already uses for its attack
    indicator score, kept consistent on purpose. Every scorer includes at
    least one distinguishing *negative* check (e.g. brute force requires
    the device to be the entity's own known device) specifically to reduce
    ties between attack types that share some indicators.
    """

    name = "rule_based"

    def classify(self, evidence: EvidenceBundle) -> ClassificationScores:
        scorers = {
            AttackType.BRUTE_FORCE: self._score_brute_force,
            AttackType.IMPOSSIBLE_TRAVEL: self._score_impossible_travel,
            AttackType.CREDENTIAL_STUFFING: self._score_credential_stuffing,
            AttackType.LATERAL_MOVEMENT: self._score_lateral_movement,
            AttackType.DEVICE_SPOOFING: self._score_device_spoofing,
            AttackType.LOW_AND_SLOW_EXFILTRATION: self._score_low_and_slow_exfiltration,
            AttackType.INSIDER_DRIFT: self._score_insider_drift,
        }
        scores: dict[AttackType, float] = {}
        matched_indicators: dict[AttackType, tuple[str, ...]] = {}
        for attack_type in KNOWN_ATTACK_TYPES:
            score, indicators = scorers[attack_type](evidence)
            scores[attack_type] = score
            matched_indicators[attack_type] = indicators
        return ClassificationScores(scores=scores, matched_indicators=matched_indicators)

    def _score_brute_force(self, e: EvidenceBundle) -> tuple[float, tuple[str, ...]]:
        device_consistent = not (e.fingerprint_mismatch or e.os_novelty or e.mac_novelty)
        checks: tuple[_Check, ...] = (
            (e.login_result == "failure", "login_result=failure"),
            (
                e.consecutive_failures >= _CONSECUTIVE_FAILURES_THRESHOLD,
                f"consecutive_failures={e.consecutive_failures} >= {_CONSECUTIVE_FAILURES_THRESHOLD}",
            ),
            (
                e.burst_access_score >= _BURST_ACCESS_THRESHOLD,
                f"burst_access_score={e.burst_access_score:.1f} >= {_BURST_ACCESS_THRESHOLD:.0f}",
            ),
            (
                e.dimension_deviations.get("authentication", 0.0) >= 0.5,
                f"authentication deviation={e.dimension_deviations.get('authentication', 0.0):.2f} >= 0.50",
            ),
            (device_consistent, "device identity matches the entity's known device"),
        )
        return _score(checks)

    def _score_credential_stuffing(self, e: EvidenceBundle) -> tuple[float, tuple[str, ...]]:
        checks: tuple[_Check, ...] = (
            (e.login_result == "failure", "login_result=failure"),
            (
                e.device_familiarity_score < 0.3,
                f"device_familiarity_score={e.device_familiarity_score:.2f} < 0.30",
            ),
            (
                e.fingerprint_mismatch or e.os_novelty or e.mac_novelty,
                "device identity inconsistent with the entity's known device",
            ),
            (
                1 <= e.consecutive_failures < 10,
                f"consecutive_failures={e.consecutive_failures} in a moderate (non-brute-force) range",
            ),
            (
                e.burst_access_score < _BURST_ACCESS_THRESHOLD,
                f"burst_access_score={e.burst_access_score:.1f} below the rapid-fire threshold",
            ),
        )
        return _score(checks)

    def _score_impossible_travel(self, e: EvidenceBundle) -> tuple[float, tuple[str, ...]]:
        checks: tuple[_Check, ...] = (
            (
                e.geo_velocity_kmh > _GEO_VELOCITY_IMPLAUSIBLE_KMH,
                f"geo_velocity_kmh={e.geo_velocity_kmh:.0f} > {_GEO_VELOCITY_IMPLAUSIBLE_KMH:.0f}",
            ),
            (e.country_change, "country_change=true"),
            (e.geo_novelty, "geo_novelty=true (location never seen before)"),
            (
                e.dimension_deviations.get("geographic", 0.0) >= 0.5,
                f"geographic deviation={e.dimension_deviations.get('geographic', 0.0):.2f} >= 0.50",
            ),
            (e.login_result == "success", "login_result=success"),
        )
        return _score(checks)

    def _score_device_spoofing(self, e: EvidenceBundle) -> tuple[float, tuple[str, ...]]:
        checks: tuple[_Check, ...] = (
            (e.fingerprint_mismatch, "fingerprint_mismatch=true"),
            (e.os_novelty or e.mac_novelty, "os_novelty or mac_novelty=true"),
            (
                e.device_familiarity_score < 0.2,
                f"device_familiarity_score={e.device_familiarity_score:.2f} < 0.20",
            ),
            (
                e.dimension_deviations.get("device", 0.0) >= 0.5,
                f"device deviation={e.dimension_deviations.get('device', 0.0):.2f} >= 0.50",
            ),
            (e.login_result == "success", "login_result=success"),
        )
        return _score(checks)

    def _score_lateral_movement(self, e: EvidenceBundle) -> tuple[float, tuple[str, ...]]:
        checks: tuple[_Check, ...] = (
            (e.resource_novelty, "resource_novelty=true (resource never seen before)"),
            (e.sensitive_resource_access, "sensitive_resource_access=true"),
            (
                e.resource_sharing_score is not None and e.resource_sharing_score < 0.2,
                f"resource_sharing_score={e.resource_sharing_score} < 0.20 against department peers",
            ),
            (
                e.resource_transition_probability is not None and e.resource_transition_probability < 0.05,
                f"resource_transition_probability={e.resource_transition_probability} < 0.05",
            ),
            (
                e.dimension_deviations.get("resource", 0.0) >= 0.5,
                f"resource deviation={e.dimension_deviations.get('resource', 0.0):.2f} >= 0.50",
            ),
        )
        return _score(checks)

    def _score_low_and_slow_exfiltration(self, e: EvidenceBundle) -> tuple[float, tuple[str, ...]]:
        checks: tuple[_Check, ...] = (
            (e.sensitive_resource_access, "sensitive_resource_access=true"),
            (e.resource_diversity >= 0.6, f"resource_diversity={e.resource_diversity:.2f} >= 0.60"),
            (
                e.historical_percentile_session_duration >= 85.0,
                f"historical_percentile_session_duration={e.historical_percentile_session_duration:.1f} >= 85",
            ),
            (
                e.burst_access_score < 5.0,
                f"burst_access_score={e.burst_access_score:.1f} < 5.0 (deliberately unhurried)",
            ),
            (
                e.dimension_deviations.get("session", 0.0) >= 0.3,
                f"session deviation={e.dimension_deviations.get('session', 0.0):.2f} >= 0.30",
            ),
        )
        return _score(checks)

    def _score_insider_drift(self, e: EvidenceBundle) -> tuple[float, tuple[str, ...]]:
        # Historical activity is evidenced two ways: a genuine rising trend
        # across stored profile versions when one exists, or simply enough
        # tenure (history_length) to have a real baseline to drift from —
        # the former needs a profile store spanning genuinely different
        # time windows to ever fire, so the latter keeps this signal live
        # even against a store built from a single point in time.
        rising_drift = len(e.drift_score_trend) >= 2 and e.drift_score_trend[-1] > e.drift_score_trend[0]
        has_tenure = e.history_length >= 10
        checks: tuple[_Check, ...] = (
            (
                e.behaviour_drift_score >= _DRIFT_SIGNIFICANCE_THRESHOLD,
                f"behaviour_drift_score={e.behaviour_drift_score:.2f} >= {_DRIFT_SIGNIFICANCE_THRESHOLD:.2f}",
            ),
            (
                e.session_entropy <= 0.1,
                f"session_entropy={e.session_entropy:.2f} <= 0.10 (routine, low-diversity command pattern)",
            ),
            (not e.new_entity_flag, "entity is established, not cold-start"),
            (e.resource_diversity >= 0.2, f"resource_diversity={e.resource_diversity:.2f} >= 0.20"),
            (
                rising_drift or has_tenure,
                f"drift_score rising across profile history {e.drift_score_trend}"
                if rising_drift
                else f"history_length={e.history_length} >= 10 (established historical baseline)",
            ),
        )
        score, matched = _score(checks)
        # session_entropy is, empirically, the single cleanest signal that
        # separates insider drift's routine, low-diversity sessions from
        # the multi-command sessions typical of lateral movement and
        # low-and-slow exfiltration — both of which otherwise share several
        # of the checks above (an established entity gradually touching a
        # more diverse resource set). When entropy clearly contradicts an
        # insider-drift read, damp the score so those attack types aren't
        # out-competed on indicators that were never specific to this one.
        if e.session_entropy > 0.5:
            score = round(score * 0.5, 4)
        return score, matched


_STRATEGY_REGISTRY: dict[str, type[ClassificationStrategy]] = {
    "rule_based": RuleBasedClassificationStrategy,
}


def build_classification_strategy(name: str) -> ClassificationStrategy:
    strategy_cls = _STRATEGY_REGISTRY.get(name)
    if strategy_cls is None:
        raise ValueError(f"Unknown classification strategy: '{name}'. Available: {sorted(_STRATEGY_REGISTRY)}")
    return strategy_cls()


class AttackClassifier:
    """Thin, swappable wrapper around whichever ClassificationStrategy is
    configured — the rest of the classification pipeline depends only on
    this class, never on a concrete strategy. Mirrors detection.anomaly_scorer's
    AnomalyScorer/ScoringStrategy split by design.
    """

    def __init__(self, strategy: ClassificationStrategy) -> None:
        self.strategy = strategy

    def classify(self, evidence: EvidenceBundle) -> ClassificationScores:
        return self.strategy.classify(evidence)