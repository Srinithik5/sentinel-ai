from __future__ import annotations

from features.entity_history import EntityHistoryTracker


def extract_session_features(tracker: EntityHistoryTracker) -> dict[str, object]:
    """Authentication-outcome features: success/failure rates, the current
    consecutive-failure streak, and MFA usage frequency — all computed from
    the entity's history strictly before the current event.
    """
    return {
        "success_ratio": round(tracker.success_ratio, 4),
        "failure_ratio": round(tracker.failure_ratio, 4),
        "consecutive_failures": tracker.consecutive_failures,
        "mfa_usage_frequency": round(tracker.mfa_usage_frequency, 4),
    }