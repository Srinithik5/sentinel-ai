from __future__ import annotations

from features.entity_history import EntityHistoryTracker


def extract_statistical_features(session_duration: float, tracker: EntityHistoryTracker) -> dict[str, object]:
    """Generic rolling/moving statistics over the entity's session_duration
    history — the expanding mean/std (Welford's algorithm, all history to
    date), a fixed-window moving average (most recent N events), and this
    event's percentile rank within the entity's historical distribution.
    """
    return {
        "rolling_mean_session_duration": round(tracker.rolling_mean_session_duration, 2),
        "rolling_std_session_duration": round(tracker.rolling_std_session_duration, 2),
        "moving_avg_session_duration": round(tracker.moving_avg_session_duration, 2),
        "historical_percentile_session_duration": round(tracker.historical_percentile(session_duration), 2),
    }