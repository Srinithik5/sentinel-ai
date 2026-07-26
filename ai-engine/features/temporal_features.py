from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from features.entity_history import EntityHistoryTracker, EntityStaticProfile


def extract_temporal_features(
    timestamp: datetime,
    session_duration: float,
    static: EntityStaticProfile | None,
    tracker: EntityHistoryTracker,
) -> dict[str, object]:
    tz = ZoneInfo(static.timezone) if static is not None else ZoneInfo("UTC")
    local_dt = timestamp.astimezone(tz)

    login_hour = local_dt.hour
    day_of_week = local_dt.weekday()
    is_weekend = day_of_week >= 5

    if static is not None and static.working_hours_start <= login_hour < static.working_hours_end:
        working_hours_deviation = 0.0
    elif static is not None:
        distance_to_start = (static.working_hours_start - login_hour) % 24
        distance_to_end = (login_hour - static.working_hours_end) % 24
        working_hours_deviation = float(min(distance_to_start, distance_to_end))
    else:
        working_hours_deviation = 0.0

    return {
        "login_hour": login_hour,
        "day_of_week": day_of_week,
        "is_weekend": is_weekend,
        "working_hours_deviation": working_hours_deviation,
        "time_since_previous_login_seconds": round(tracker.time_since_previous_login_seconds(timestamp), 2),
        "session_duration_zscore": round(tracker.session_duration_zscore(session_duration), 4),
    }