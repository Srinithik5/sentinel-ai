from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

_HISTORY_LENGTH_BINS: tuple[tuple[int, int | None, str], ...] = (
    (0, 5, "0-5"),
    (5, 10, "5-10"),
    (10, 20, "10-20"),
    (20, 50, "20-50"),
    (50, 100, "50-100"),
    (100, None, "100+"),
)

_CONFIDENCE_BINS: tuple[tuple[float, float, str], ...] = (
    (0.0, 0.2, "0.0-0.2"),
    (0.2, 0.4, "0.2-0.4"),
    (0.4, 0.6, "0.4-0.6"),
    (0.6, 0.8, "0.6-0.8"),
    (0.8, 1.01, "0.8-1.0"),
)


@dataclass(frozen=True)
class ColdStartSegment:
    """Detection behaviour for one entity population segment (new users,
    new devices, new service accounts, or an established baseline for
    comparison)."""

    segment_name: str
    event_count: int
    avg_risk_score: float
    avg_anomaly_score: float
    flagged_rate: float
    false_positive_rate: float | None

    def to_dict(self) -> dict[str, object]:
        return {
            "segment_name": self.segment_name,
            "event_count": self.event_count,
            "avg_risk_score": self.avg_risk_score,
            "avg_anomaly_score": self.avg_anomaly_score,
            "flagged_rate": self.flagged_rate,
            "false_positive_rate": self.false_positive_rate,
        }


@dataclass(frozen=True)
class WarmupBucket:
    """Detection behaviour bucketed by an entity's history length at the
    time of the event — the "warm-up curve" showing how risk scoring
    changes as an entity accumulates a real baseline.
    """

    history_length_range: str
    event_count: int
    avg_risk_score: float
    avg_historical_confidence: float

    def to_dict(self) -> dict[str, object]:
        return {
            "history_length_range": self.history_length_range,
            "event_count": self.event_count,
            "avg_risk_score": self.avg_risk_score,
            "avg_historical_confidence": self.avg_historical_confidence,
        }


@dataclass(frozen=True)
class CalibrationBin:
    """One bin of a confidence-calibration (reliability) curve: within
    events whose historical_confidence fell in this range, how often was
    the detection verdict actually correct against ground truth?
    """

    confidence_range: str
    event_count: int
    avg_confidence: float
    empirical_accuracy: float | None

    def to_dict(self) -> dict[str, object]:
        return {
            "confidence_range": self.confidence_range,
            "event_count": self.event_count,
            "avg_confidence": self.avg_confidence,
            "empirical_accuracy": self.empirical_accuracy,
        }


@dataclass(frozen=True)
class ColdStartEvaluationResult:
    segments: tuple[ColdStartSegment, ...]
    warmup_curve: tuple[WarmupBucket, ...]
    calibration_curve: tuple[CalibrationBin, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "segments": [segment.to_dict() for segment in self.segments],
            "warmup_curve": [bucket.to_dict() for bucket in self.warmup_curve],
            "calibration_curve": [bucket.to_dict() for bucket in self.calibration_curve],
        }


class ColdStartEvaluator:
    """Evaluates detection behaviour for cold-start populations (new
    users, new devices, new service accounts), the warm-up trend as
    entities accumulate history, and confidence calibration — all
    computed from a merged Phase 4 detection + Phase 2C feature table.
    Every input column here is real and already computed by earlier
    phases; nothing is re-derived or simulated.
    """

    def evaluate(self, merged_df: pd.DataFrame) -> ColdStartEvaluationResult:
        segments = (
            self._segment("New Users", merged_df[(merged_df["entity_type"] == "user") & (merged_df["new_entity_flag"])]),
            self._segment(
                "New Service Accounts",
                merged_df[(merged_df["entity_type"] == "service_account") & (merged_df["new_entity_flag"])],
            ),
            self._segment("New Devices (fingerprint novel)", merged_df[merged_df["fingerprint_mismatch"]]),
            self._segment("Established Baseline", merged_df[~merged_df["new_entity_flag"]]),
        )

        warmup_curve = self._warmup_curve(merged_df)
        calibration_curve = self._calibration_curve(merged_df)

        return ColdStartEvaluationResult(segments=segments, warmup_curve=warmup_curve, calibration_curve=calibration_curve)

    def _segment(self, name: str, subset: pd.DataFrame) -> ColdStartSegment:
        if subset.empty:
            return ColdStartSegment(name, 0, 0.0, 0.0, 0.0, None)

        flagged = subset["verdict"] != "normal"
        labeled = subset[subset["is_attack"].notna()]
        false_positive_rate = None
        if not labeled.empty:
            labeled_flagged = labeled["verdict"] != "normal"
            negatives = labeled[~labeled["is_attack"].astype(bool)]
            if len(negatives) > 0:
                false_positive_rate = round(float((negatives["verdict"] != "normal").mean()), 6)

        return ColdStartSegment(
            segment_name=name,
            event_count=len(subset),
            avg_risk_score=round(float(subset["risk_score"].mean()), 4),
            avg_anomaly_score=round(float(subset["anomaly_score"].mean()), 4),
            flagged_rate=round(float(flagged.mean()), 6),
            false_positive_rate=false_positive_rate,
        )

    def _warmup_curve(self, df: pd.DataFrame) -> tuple[WarmupBucket, ...]:
        buckets: list[WarmupBucket] = []
        for low, high, label in _HISTORY_LENGTH_BINS:
            if high is None:
                mask = df["history_length"] >= low
            else:
                mask = (df["history_length"] >= low) & (df["history_length"] < high)
            subset = df[mask]
            if subset.empty:
                continue
            buckets.append(
                WarmupBucket(
                    history_length_range=label,
                    event_count=len(subset),
                    avg_risk_score=round(float(subset["risk_score"].mean()), 4),
                    avg_historical_confidence=round(float(subset["historical_confidence"].mean()), 4),
                )
            )
        return tuple(buckets)

    def _calibration_curve(self, df: pd.DataFrame) -> tuple[CalibrationBin, ...]:
        labeled = df[df["is_attack"].notna()]
        bins: list[CalibrationBin] = []
        for low, high, label in _CONFIDENCE_BINS:
            mask_all = (df["historical_confidence"] >= low) & (df["historical_confidence"] < high)
            subset_all = df[mask_all]
            if subset_all.empty:
                continue

            mask_labeled = (labeled["historical_confidence"] >= low) & (labeled["historical_confidence"] < high)
            subset_labeled = labeled[mask_labeled]
            empirical_accuracy = None
            if not subset_labeled.empty:
                predicted_flagged = subset_labeled["verdict"] != "normal"
                actual_attack = subset_labeled["is_attack"].astype(bool)
                empirical_accuracy = round(float((predicted_flagged == actual_attack).mean()), 6)

            bins.append(
                CalibrationBin(
                    confidence_range=label,
                    event_count=len(subset_all),
                    avg_confidence=round(float(subset_all["historical_confidence"].mean()), 4),
                    empirical_accuracy=empirical_accuracy,
                )
            )
        return tuple(bins)


_MERGE_FEATURE_COLUMNS: tuple[str, ...] = (
    "event_id",
    "entity_type",
    "new_entity_flag",
    "fingerprint_mismatch",
    "history_length",
)


def build_cold_start_input(detection_df: pd.DataFrame, events_df: pd.DataFrame) -> pd.DataFrame:
    """Merges Phase 4 detection results with the Phase 2C feature columns
    a cold-start evaluation needs. `detection_df` already carries
    `entity_type`, but the entity-type-at-event-time from the raw feature
    file is used here for consistency with `new_entity_flag`/
    `fingerprint_mismatch`/`history_length`, all of which only exist in
    the Phase 2C file.
    """
    missing_events = set(_MERGE_FEATURE_COLUMNS) - set(events_df.columns)
    if missing_events:
        raise ValueError(f"engineered events file is missing required columns: {sorted(missing_events)}")

    feature_subset = events_df[list(_MERGE_FEATURE_COLUMNS)]
    merged = detection_df.merge(feature_subset, on="event_id", how="inner", suffixes=("_detection", ""))
    if "entity_type" not in merged.columns:
        raise ValueError("Merged cold-start input is missing 'entity_type' after merge.")
    return merged