from __future__ import annotations

import pandas as pd


def build_behavior_profile_summary(entities_df: pd.DataFrame, events_df: pd.DataFrame) -> pd.DataFrame:
    events = events_df.copy()
    events["timestamp"] = pd.to_datetime(events["timestamp"], format="ISO8601")
    events["hour"] = events["timestamp"].dt.hour
    events["weekday"] = events["timestamp"].dt.weekday
    events["is_weekend"] = events["weekday"] >= 5
    events["is_failure"] = events["login_result"] == "failure"

    grouped = events.groupby("entity_id")

    summary = pd.concat(
        [
            grouped.size().rename("total_events"),
            grouped["resource_accessed"].nunique().rename("unique_resources_used"),
            grouped["resource_accessed"]
            .agg(lambda values: values.value_counts().idxmax())
            .rename("top_resource"),
            grouped["device_fingerprint"].nunique().rename("unique_devices_used"),
            grouped["hour"].agg(lambda values: int(values.value_counts().idxmax())).rename("most_common_hour"),
            grouped["is_weekend"].mean().rename("weekend_event_ratio"),
            grouped["is_failure"].mean().rename("login_failure_rate"),
            grouped["session_duration"].mean().rename("avg_session_duration_seconds"),
            grouped["timestamp"].min().rename("first_event_at"),
            grouped["timestamp"].max().rename("last_event_at"),
        ],
        axis=1,
    ).reset_index()

    span_days = max((events["timestamp"].max() - events["timestamp"].min()).days, 1)
    summary["avg_events_per_day"] = summary["total_events"] / span_days

    entity_attributes = entities_df[
        ["entity_id", "entity_type", "department", "role", "privilege_level", "is_remote"]
    ]
    return entity_attributes.merge(summary, on="entity_id", how="left")