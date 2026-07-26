from __future__ import annotations

from dataclasses import dataclass

from explainability.confidence_explainer import ConfidenceExplanation
from explainability.evidence_aggregator import ExplainabilityEvidence
from explainability.feature_attribution import FeatureContribution
from explainability.reason_generator import NarrativeExplanation
from explainability.recommendation_engine import RecommendedAction

_TOP_INDICATOR_COUNT = 3


@dataclass(frozen=True)
class AnalystSummary:
    """The final, structured, analyst-facing report for one event —
    everything required to triage it without opening any other file."""

    event_id: str
    entity_id: str
    entity_type: str | None
    timestamp: str
    risk_score: float
    attack_type: str
    display_name: str
    confidence: float
    confidence_level: str
    severity: str
    mitre_tactic: str
    mitre_technique: str
    top_indicators: tuple[str, ...]
    evidence_summary: str
    recommended_actions: tuple[str, ...]
    confidence_explanation: str

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "timestamp": self.timestamp,
            "risk_score": self.risk_score,
            "attack_type": self.attack_type,
            "display_name": self.display_name,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level,
            "severity": self.severity,
            "mitre_tactic": self.mitre_tactic,
            "mitre_technique": self.mitre_technique,
            "top_indicators": " | ".join(self.top_indicators),
            "evidence_summary": self.evidence_summary,
            "recommended_actions": " | ".join(self.recommended_actions),
            "confidence_explanation": self.confidence_explanation,
        }

    def to_text(self) -> str:
        lines = [
            f"Entity: {self.entity_id} ({self.entity_type or 'unknown type'})",
            f"Event: {self.event_id} at {self.timestamp}",
            f"Risk Score: {self.risk_score:.1f}/100 ({self.severity})",
            f"Attack Type: {self.display_name} (confidence: {self.confidence:.0%}, {self.confidence_level})",
            f"MITRE ATT&CK: {self.mitre_tactic} / {self.mitre_technique}",
            "Top Behavioural Indicators:",
        ]
        lines.extend(f"  {index}. {indicator}" for index, indicator in enumerate(self.top_indicators, start=1))
        lines.append(f"Evidence Summary: {self.evidence_summary}")
        lines.append(f"Confidence: {self.confidence_explanation}")
        lines.append("Recommended Actions:")
        lines.extend(f"  - {action}" for action in self.recommended_actions)
        return "\n".join(lines)


class AnalystSummaryBuilder:
    """Assembles the final AnalystSummary from every other module's output
    — a pure aggregation step with no scoring or decision logic of its own.
    """

    def build(
        self,
        *,
        evidence: ExplainabilityEvidence,
        contributions: tuple[FeatureContribution, ...],
        narrative: NarrativeExplanation,
        confidence_explanation: ConfidenceExplanation,
        recommendations: tuple[RecommendedAction, ...],
    ) -> AnalystSummary:
        top_indicators = tuple(
            f"{c.dimension} ({c.contribution_percentage:.1f}%): {c.explanation}"
            for c in contributions[:_TOP_INDICATOR_COUNT]
        )
        recommended_actions = tuple(f"[{a.priority}] {a.action} — {a.rationale}" for a in recommendations)

        return AnalystSummary(
            event_id=evidence.event_id,
            entity_id=evidence.entity_id,
            entity_type=evidence.entity_type,
            timestamp=evidence.timestamp,
            risk_score=evidence.detection.risk_score,
            attack_type=evidence.classification.attack_type,
            display_name=evidence.classification.display_name,
            confidence=evidence.classification.confidence,
            confidence_level=confidence_explanation.level.value,
            severity=evidence.detection.severity,
            mitre_tactic=evidence.classification.mitre_tactic,
            mitre_technique=evidence.classification.mitre_technique,
            top_indicators=top_indicators,
            evidence_summary=narrative.to_paragraph(),
            recommended_actions=recommended_actions,
            confidence_explanation=confidence_explanation.narrative,
        )