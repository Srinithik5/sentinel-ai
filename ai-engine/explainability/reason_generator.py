from __future__ import annotations

from dataclasses import dataclass

from explainability.evidence_aggregator import ExplainabilityEvidence
from explainability.feature_attribution import FeatureContribution

_TOP_CONTRIBUTOR_COUNT = 3


@dataclass(frozen=True)
class NarrativeExplanation:
    """Four natural-language statements answering the required questions:
    how much did behaviour deviate, how does that compare to the entity's
    own history, which features drove it, and what generic attack
    indicators are present.
    """

    behaviour_deviation: str
    historical_comparison: str
    feature_impact: str
    attack_indicators: str

    def to_paragraph(self) -> str:
        return " ".join((self.behaviour_deviation, self.historical_comparison, self.feature_impact, self.attack_indicators))

    def to_dict(self) -> dict[str, object]:
        return {
            "behaviour_deviation": self.behaviour_deviation,
            "historical_comparison": self.historical_comparison,
            "feature_impact": self.feature_impact,
            "attack_indicators": self.attack_indicators,
        }


class ReasonGenerator:
    """Turns an ExplainabilityEvidence bundle and its feature attribution
    into a structured, human-readable narrative. Every sentence traces
    back to an already-computed Phase 4/5 value or a Phase 2C/3 fact —
    nothing here re-derives a score or a verdict.
    """

    def generate(
        self,
        evidence: ExplainabilityEvidence,
        contributions: tuple[FeatureContribution, ...],
    ) -> NarrativeExplanation:
        return NarrativeExplanation(
            behaviour_deviation=self._behaviour_deviation(evidence),
            historical_comparison=self._historical_comparison(evidence),
            feature_impact=self._feature_impact(contributions),
            attack_indicators=self._attack_indicators(evidence),
        )

    def _behaviour_deviation(self, evidence: ExplainabilityEvidence) -> str:
        d = evidence.detection
        return (
            f"This event scored an anomaly of {d.anomaly_score:.2f} on a 0-1 scale and a risk score of "
            f"{d.risk_score:.1f} out of 100, resulting in a '{d.verdict}' verdict at '{d.severity}' severity."
        )

    def _historical_comparison(self, evidence: ExplainabilityEvidence) -> str:
        p = evidence.profile
        h = evidence.history

        if not p.has_profile:
            return "No behaviour profile exists yet for this entity — this event was compared against a neutral baseline only."

        trend_clause = ""
        if len(h.drift_score_trend) >= 2:
            direction = "rising" if h.drift_score_trend[-1] > h.drift_score_trend[0] else "stable or falling"
            formatted_trend = ", ".join(f"{value:.2f}" for value in h.drift_score_trend)
            trend_clause = (
                f" Drift across the entity's {h.profile_version_count} stored profile versions is "
                f"{direction} ({formatted_trend})."
            )

        return (
            f"The entity's behaviour profile is on version {p.profile_version} ('{p.warmup_strategy}' status) "
            f"with a current baseline drift score of {p.drift_score:.2f}.{trend_clause}"
        )

    def _feature_impact(self, contributions: tuple[FeatureContribution, ...]) -> str:
        top = contributions[:_TOP_CONTRIBUTOR_COUNT]
        parts = [f"{c.dimension} ({c.contribution_percentage:.1f}%): {c.explanation}" for c in top]
        return "Top contributing behavioural dimensions — " + " | ".join(parts)

    def _attack_indicators(self, evidence: ExplainabilityEvidence) -> str:
        d = evidence.detection
        c = evidence.classification
        indicator_percentage = d.risk_indicator_component * 100
        matched = ", ".join(c.matched_indicators) if c.matched_indicators else "no indicators matched a known attack signature strongly enough"
        return (
            f"Phase 4's generic attack-indicator score is {indicator_percentage:.0f}% of independent red flags "
            f"present (consecutive failures, device/OS/MAC novelty, implausible travel speed, burst access). "
            f"Phase 5 classification evidence: {matched}."
        )