from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

_RISK_BIN_WIDTH = 10
_TOP_N = 10


@dataclass(frozen=True)
class DistributionEntry:
    label: str
    count: int

    def to_dict(self) -> dict[str, object]:
        return {"label": self.label, "count": self.count}


@dataclass(frozen=True)
class HourlyActivityEntry:
    hour: int
    total_events: int
    anomalous_events: int

    def to_dict(self) -> dict[str, object]:
        return {"hour": self.hour, "totalEvents": self.total_events, "anomalousEvents": self.anomalous_events}


@dataclass(frozen=True)
class AnalyticsData:
    attack_distribution: tuple[DistributionEntry, ...]
    severity_distribution: tuple[DistributionEntry, ...]
    risk_distribution: tuple[DistributionEntry, ...]
    hourly_activity: tuple[HourlyActivityEntry, ...]
    top_resources: tuple[DistributionEntry, ...]
    geo_distribution: tuple[DistributionEntry, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "attackDistribution": [entry.to_dict() for entry in self.attack_distribution],
            "severityDistribution": [entry.to_dict() for entry in self.severity_distribution],
            "riskDistribution": [entry.to_dict() for entry in self.risk_distribution],
            "hourlyActivity": [entry.to_dict() for entry in self.hourly_activity],
            "topResources": [entry.to_dict() for entry in self.top_resources],
            "geoDistribution": [entry.to_dict() for entry in self.geo_distribution],
        }


def _distribution(counts: "pd.Series[int]") -> tuple[DistributionEntry, ...]:
    return tuple(DistributionEntry(label=str(label), count=int(count)) for label, count in counts.items())


def build_analytics(detection_df: pd.DataFrame, classification_df: pd.DataFrame, events_df: pd.DataFrame) -> AnalyticsData:
    flagged = detection_df[detection_df["verdict"] != "normal"]
    flagged_event_ids = set(flagged["event_id"])

    attack_distribution = _distribution(classification_df["attack_type"].value_counts())
    severity_distribution = _distribution(flagged["severity"].value_counts())

    risk_bins = list(range(0, 101, _RISK_BIN_WIDTH))
    risk_labels = [f"{lo}-{lo + _RISK_BIN_WIDTH}" for lo in risk_bins[:-1]]
    risk_hist = pd.cut(detection_df["risk_score"], bins=risk_bins, labels=risk_labels, include_lowest=True)
    risk_distribution = _distribution(risk_hist.value_counts().sort_index())

    total_by_hour = events_df["login_hour"].value_counts().sort_index().to_dict()
    flagged_events = events_df[events_df["event_id"].isin(flagged_event_ids)]
    anomalous_by_hour = flagged_events["login_hour"].value_counts().sort_index().to_dict()
    hourly_activity = tuple(
        HourlyActivityEntry(
            hour=hour, total_events=int(total_by_hour.get(hour, 0)), anomalous_events=int(anomalous_by_hour.get(hour, 0))
        )
        for hour in range(24)
    )

    top_resources = _distribution(flagged_events["resource_accessed"].value_counts().head(_TOP_N))
    geo_distribution = _distribution(flagged_events["geo_location"].value_counts().head(_TOP_N))

    return AnalyticsData(
        attack_distribution=attack_distribution,
        severity_distribution=severity_distribution,
        risk_distribution=risk_distribution,
        hourly_activity=hourly_activity,
        top_resources=top_resources,
        geo_distribution=geo_distribution,
    )