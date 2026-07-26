from __future__ import annotations

from abc import ABC, abstractmethod

from detection.profile_comparator import DimensionDeviation

_DEFAULT_DIMENSION_WEIGHTS: dict[str, float] = {
    "temporal": 1.0,
    "device": 1.2,
    "resource": 1.2,
    "geographic": 1.5,
    "authentication": 1.3,
    "session": 0.8,
}


class ScoringStrategy(ABC):
    """A pluggable method for collapsing per-dimension deviations into one
    anomaly score. New strategies (e.g. a trained isolation-forest scorer)
    plug in by implementing this interface — AnomalyScorer and everything
    upstream of it never needs to change (open/closed principle).
    """

    name: str

    @abstractmethod
    def score(self, deviations: tuple[DimensionDeviation, ...]) -> float:
        """Returns a single anomaly score in [0.0, 1.0]."""


class WeightedAverageScoringStrategy(ScoringStrategy):
    """Weighted mean of per-dimension deviations — the default strategy.
    Dimensions with historically stronger security signal (geographic,
    authentication) are weighted above noisier ones (session).
    """

    name = "weighted_average"

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = weights or dict(_DEFAULT_DIMENSION_WEIGHTS)

    def score(self, deviations: tuple[DimensionDeviation, ...]) -> float:
        if not deviations:
            return 0.0
        total_weight = sum(self.weights.get(deviation.dimension, 1.0) for deviation in deviations)
        if total_weight <= 0:
            return 0.0
        weighted_sum = sum(
            deviation.deviation_score * self.weights.get(deviation.dimension, 1.0) for deviation in deviations
        )
        return round(weighted_sum / total_weight, 4)


class MaxDeviationScoringStrategy(ScoringStrategy):
    """The single most deviant dimension drives the whole score — useful
    when one severe signal (e.g. a brand-new device) shouldn't be diluted
    by five unremarkable ones.
    """

    name = "max_deviation"

    def score(self, deviations: tuple[DimensionDeviation, ...]) -> float:
        if not deviations:
            return 0.0
        return round(max(deviation.deviation_score for deviation in deviations), 4)


_STRATEGY_REGISTRY: dict[str, type[ScoringStrategy]] = {
    "weighted_average": WeightedAverageScoringStrategy,
    "max_deviation": MaxDeviationScoringStrategy,
}


def build_scoring_strategy(name: str) -> ScoringStrategy:
    strategy_cls = _STRATEGY_REGISTRY.get(name)
    if strategy_cls is None:
        raise ValueError(f"Unknown scoring strategy: '{name}'. Available: {sorted(_STRATEGY_REGISTRY)}")
    return strategy_cls()


class AnomalyScorer:
    """Thin, swappable wrapper around whichever ScoringStrategy is
    configured — the rest of the detection pipeline depends only on this
    class, never on a concrete strategy.
    """

    def __init__(self, strategy: ScoringStrategy) -> None:
        self.strategy = strategy

    def compute_score(self, deviations: tuple[DimensionDeviation, ...]) -> float:
        return self.strategy.score(deviations)