from __future__ import annotations

from dataclasses import dataclass

from explainability.evidence_aggregator import ExplainabilityEvidence

_DIMENSION_NAMES: tuple[str, ...] = ("temporal", "device", "resource", "geographic", "authentication", "session")


@dataclass(frozen=True)
class FeatureContribution:
    """One behavioural dimension's share of the overall anomaly, with a
    normalized percentage and a plain-language explanation of the specific
    feature values behind it.
    """

    dimension: str
    raw_deviation: float
    contribution_percentage: float
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return {
            "dimension": self.dimension,
            "raw_deviation": self.raw_deviation,
            "contribution_percentage": self.contribution_percentage,
            "explanation": self.explanation,
        }


class FeatureAttributionEngine:
    """Ranks Phase 4's six deviation dimensions by how much each
    contributed to the overall anomaly, normalizes them into percentages
    that sum to exactly 100, and explains each one using the underlying
    Phase 2C feature values and Phase 3 profile — never a second scoring
    computation, purely an explanation of the one detection already made.
    """

    def attribute(self, evidence: ExplainabilityEvidence) -> tuple[FeatureContribution, ...]:
        deviations = evidence.detection.dimension_deviations
        total = sum(deviations.get(dimension, 0.0) for dimension in _DIMENSION_NAMES)

        if total <= 0:
            equal_share = round(100.0 / len(_DIMENSION_NAMES), 2)
            percentages = {dimension: equal_share for dimension in _DIMENSION_NAMES}
        else:
            percentages = {
                dimension: round(deviations.get(dimension, 0.0) / total * 100, 2) for dimension in _DIMENSION_NAMES
            }
            # Rounding can leave the total a few hundredths off 100 — assign
            # the remainder to the largest contributor rather than silently
            # letting the reported percentages fail to sum to 100.
            remainder = round(100.0 - sum(percentages.values()), 2)
            if remainder != 0:
                largest_dimension = max(percentages, key=lambda d: percentages[d])
                percentages[largest_dimension] = round(percentages[largest_dimension] + remainder, 2)

        contributions = tuple(
            FeatureContribution(
                dimension=dimension,
                raw_deviation=deviations.get(dimension, 0.0),
                contribution_percentage=percentages[dimension],
                explanation=self._explain(dimension, evidence),
            )
            for dimension in _DIMENSION_NAMES
        )
        return tuple(sorted(contributions, key=lambda c: c.contribution_percentage, reverse=True))

    def _explain(self, dimension: str, evidence: ExplainabilityEvidence) -> str:
        f = evidence.features
        p = evidence.profile

        if dimension == "temporal":
            if p.avg_login_hour is not None:
                return (
                    f"Login at hour {f.login_hour} vs entity average {p.avg_login_hour:.1f} "
                    f"(std {p.login_hour_std:.1f}h); working_hours_deviation={f.working_hours_deviation:.1f}h."
                )
            return f"Login at hour {f.login_hour}; no established temporal baseline yet for this entity."

        if dimension == "device":
            return self._frequency_based_explanation(
                subject=f"Device '{f.device_fingerprint}'",
                frequency=p.device_frequency,
                is_causally_novel=f.fingerprint_mismatch,
                novelty_note="first appearance of this fingerprint in the entity's event history up to this point",
            )

        if dimension == "resource":
            sensitivity = " (a sensitive resource)" if f.sensitive_resource_access else ""
            return self._frequency_based_explanation(
                subject=f"Resource '{f.resource_accessed}'{sensitivity}",
                frequency=p.resource_frequency,
                is_causally_novel=f.resource_novelty,
                novelty_note="first access to this resource in the entity's event history up to this point",
            )

        if dimension == "geographic":
            return self._frequency_based_explanation(
                subject=f"Location '{f.geo_location}'",
                frequency=p.geo_frequency,
                is_causally_novel=f.geo_novelty,
                novelty_note=f"first appearance of this location in the entity's event history; implied travel speed {f.geo_velocity_kmh:.0f} km/h",
            )

        if dimension == "authentication":
            if f.login_result == "failure":
                rate = p.failure_rate if p.failure_rate is not None else 0.0
                return f"Login failed; entity's historical failure rate is {rate:.1%}."
            return "Login succeeded; no authentication deviation."

        if dimension == "session":
            if p.avg_session_duration is not None:
                return (
                    f"Session duration {f.session_duration:.0f}s vs entity average "
                    f"{p.avg_session_duration:.0f}s (std {p.session_duration_std:.0f}s)."
                )
            return f"Session duration {f.session_duration:.0f}s; no established session baseline yet."

        return f"{dimension} deviation={evidence.detection.dimension_deviations.get(dimension, 0.0):.2f}."

    def _frequency_based_explanation(
        self,
        *,
        subject: str,
        frequency: float | None,
        is_causally_novel: bool,
        novelty_note: str,
    ) -> str:
        """Device/resource/geographic deviations are all scored by Phase 4
        from the entity's aggregate Phase 3 profile frequency — so the
        primary explanation must always lead with that frequency, the
        actual driver of the score. Phase 2C's causal "never seen yet"
        flag is a genuinely different, sequential signal (computed from
        history strictly before this event, not the full profile) and can
        legitimately disagree with the aggregate frequency — it is appended
        as context, never substituted for the frequency-based explanation,
        so the text never contradicts the deviation score it explains.
        """
        if frequency is None:
            base = f"{subject} — no established profile baseline yet."
        elif frequency <= 0.0:
            base = f"{subject} does not appear in this entity's behaviour profile at all."
        else:
            base = f"{subject} appears in {frequency:.1%} of this entity's profiled sessions."

        if is_causally_novel:
            base += f" ({novelty_note.capitalize()}.)"
        return base