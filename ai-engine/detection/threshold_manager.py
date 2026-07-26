from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SeverityLevel(str, Enum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ThresholdConfig:
    """Defaults are calibrated against the empirical risk_score distribution
    produced by RiskEngine on real generated traffic (Phase 2/2B/2C data run
    through Phase 3 profiles): normal events cluster under ~5, with a long
    tail that rarely exceeds ~31 even at the 99.9th percentile, while
    confirmed attack events land at ~21-58. These boundaries are fully
    configurable — override ThresholdConfig for a different risk-appetite
    or a differently-distributed deployment.
    """

    informational: float = 5.0
    low: float = 10.0
    medium: float = 25.0
    high: float = 45.0
    critical: float = 55.0

    def __post_init__(self) -> None:
        ordered = (self.informational, self.low, self.medium, self.high, self.critical)
        if list(ordered) != sorted(ordered):
            raise ValueError(
                "Threshold levels must be strictly increasing: informational < low < medium < high < critical, "
                f"got {ordered}"
            )
        if not all(0.0 <= value <= 100.0 for value in ordered):
            raise ValueError("All threshold levels must fall within [0, 100].")


class ThresholdManager:
    """Owns the configurable risk-score boundaries for the 5 required
    severity levels. DecisionEngine derives its 3-state verdict from these
    same boundaries rather than defining a second, potentially
    inconsistent set of cutoffs.
    """

    def __init__(self, config: ThresholdConfig | None = None) -> None:
        self.config = config or ThresholdConfig()

    def severity_for(self, risk_score: float) -> SeverityLevel:
        if risk_score >= self.config.critical:
            return SeverityLevel.CRITICAL
        if risk_score >= self.config.high:
            return SeverityLevel.HIGH
        if risk_score >= self.config.medium:
            return SeverityLevel.MEDIUM
        if risk_score >= self.config.low:
            return SeverityLevel.LOW
        return SeverityLevel.INFORMATIONAL