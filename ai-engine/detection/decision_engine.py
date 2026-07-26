from __future__ import annotations

from enum import Enum

from detection.threshold_manager import SeverityLevel, ThresholdManager


class DetectionVerdict(str, Enum):
    NORMAL = "normal"
    SUSPICIOUS = "suspicious"
    ANOMALOUS = "anomalous"


class DecisionEngine:
    """Determines Normal / Suspicious / Anomalous from a risk score, using
    ThresholdManager's configurable severity boundaries. This module
    answers exactly one question — "is this anomalous?" — and deliberately
    stops there: it has no notion of attack type, only of how far past the
    configured thresholds a risk score falls.
    """

    def __init__(self, threshold_manager: ThresholdManager) -> None:
        self.threshold_manager = threshold_manager

    def decide(self, risk_score: float) -> DetectionVerdict:
        severity = self.threshold_manager.severity_for(risk_score)
        if severity in (SeverityLevel.HIGH, SeverityLevel.CRITICAL):
            return DetectionVerdict.ANOMALOUS
        if severity == SeverityLevel.MEDIUM:
            return DetectionVerdict.SUSPICIOUS
        return DetectionVerdict.NORMAL