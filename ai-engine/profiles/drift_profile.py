from __future__ import annotations

from dataclasses import dataclass

from profiles.statistical_profile import StatisticalProfile

_DRIFT_SIGNIFICANCE_THRESHOLD = 0.35


@dataclass(frozen=True)
class DriftProfile:
    profile_version: int
    drift_score: float
    adaptation_window_days: int
    historical_sample_count: int
    current_sample_count: int
    drifted_dimensions: tuple[str, ...]
    is_significant_drift: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "profile_version": self.profile_version,
            "drift_score": self.drift_score,
            "adaptation_window_days": self.adaptation_window_days,
            "historical_sample_count": self.historical_sample_count,
            "current_sample_count": self.current_sample_count,
            "drifted_dimensions": list(self.drifted_dimensions),
            "is_significant_drift": self.is_significant_drift,
        }

    @staticmethod
    def from_dict(data: dict[str, object]) -> "DriftProfile":
        return DriftProfile(
            profile_version=int(data["profile_version"]),
            drift_score=float(data["drift_score"]),
            adaptation_window_days=int(data["adaptation_window_days"]),
            historical_sample_count=int(data["historical_sample_count"]),
            current_sample_count=int(data["current_sample_count"]),
            drifted_dimensions=tuple(data["drifted_dimensions"]),
            is_significant_drift=bool(data["is_significant_drift"]),
        )


def _distribution_distance(historical: dict[str, float], current: dict[str, float]) -> float:
    """1 - cosine similarity between two frequency distributions, treated as
    sparse vectors over their combined key space. 0.0 = identical
    distributions, 1.0 = completely disjoint.
    """
    keys = set(historical) | set(current)
    if not keys:
        return 0.0
    dot = sum(historical.get(key, 0.0) * current.get(key, 0.0) for key in keys)
    historical_norm = sum(value**2 for value in historical.values()) ** 0.5
    current_norm = sum(value**2 for value in current.values()) ** 0.5
    if historical_norm == 0.0 or current_norm == 0.0:
        return 1.0 if historical_norm != current_norm else 0.0
    cosine_similarity = dot / (historical_norm * current_norm)
    return round(max(0.0, 1.0 - cosine_similarity), 4)


def compute_drift(
    *,
    historical: StatisticalProfile | None,
    current: StatisticalProfile,
    previous_version: int,
    adaptation_window_days: int,
) -> DriftProfile:
    """Compares a stored historical StatisticalProfile against a freshly
    computed current one. With no historical profile (first run for this
    entity), drift is defined as zero — there is nothing yet to have
    drifted from. The current profile always becomes the new active
    baseline regardless of drift_score: this function only ever reports
    drift, it never blocks the profile from adapting.
    """
    if historical is None or historical.sample_count == 0:
        return DriftProfile(
            profile_version=previous_version + 1,
            drift_score=0.0,
            adaptation_window_days=adaptation_window_days,
            historical_sample_count=0,
            current_sample_count=current.sample_count,
            drifted_dimensions=(),
            is_significant_drift=False,
        )

    dimension_distances: dict[str, float] = {
        "resource_frequency": _distribution_distance(historical.resource_frequency, current.resource_frequency),
        "device_frequency": _distribution_distance(historical.device_frequency, current.device_frequency),
        "geo_frequency": _distribution_distance(historical.geo_frequency, current.geo_frequency),
        "login_hour": min(1.0, abs(historical.avg_login_hour - current.avg_login_hour) / 12.0),
        "failure_rate": min(1.0, abs(historical.failure_rate - current.failure_rate)),
    }

    drift_score = round(sum(dimension_distances.values()) / len(dimension_distances), 4)
    drifted_dimensions = tuple(
        sorted(name for name, distance in dimension_distances.items() if distance >= _DRIFT_SIGNIFICANCE_THRESHOLD)
    )

    return DriftProfile(
        profile_version=previous_version + 1,
        drift_score=drift_score,
        adaptation_window_days=adaptation_window_days,
        historical_sample_count=historical.sample_count,
        current_sample_count=current.sample_count,
        drifted_dimensions=drifted_dimensions,
        is_significant_drift=drift_score >= _DRIFT_SIGNIFICANCE_THRESHOLD,
    )