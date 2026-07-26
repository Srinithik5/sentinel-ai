from __future__ import annotations


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def normalize_zscore(value: float, mean: float, std: float, *, cap: float = 3.0) -> float:
    """Maps a raw value's distance from (mean, std) into a 0.0-1.0 deviation
    score, saturating at `cap` standard deviations. Returns 0.0 when std is
    non-positive (insufficient history to have a meaningful spread) — the
    caller decides separately whether that itself deserves a deviation
    score via a different comparison.
    """
    if std <= 0:
        return 0.0
    z = abs(value - mean) / std
    return clamp(z / cap)


def normalize_circular_distance(value: float, reference: float, *, period: float, cap_fraction: float = 0.5) -> float:
    """Like normalize_zscore but for cyclical values (e.g. hour-of-day on a
    24h clock), where distance wraps around `period` instead of growing
    unboundedly.
    """
    if period <= 0:
        return 0.0
    raw_distance = abs(value - reference)
    wrapped_distance = min(raw_distance, period - raw_distance)
    cap = period * cap_fraction
    return clamp(wrapped_distance / cap) if cap > 0 else 0.0


def normalize_frequency(frequency: float) -> float:
    """Converts a 0.0-1.0 historical frequency into a 0.0-1.0 deviation
    score: a frequently-seen value is not deviant, a rare or unseen one is.
    """
    return clamp(1.0 - frequency)


def scale_to_risk_score(normalized_value: float) -> float:
    """Converts a 0.0-1.0 normalized composite into the required 0-100 risk
    score.
    """
    return round(100 * clamp(normalized_value), 2)