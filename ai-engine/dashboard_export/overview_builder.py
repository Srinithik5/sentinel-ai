from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from detection.detection_engine import DetectionEngineConfig, build_detection_engine
from detection.profile_comparator import event_record_from_row
from detection.stream_processor import StreamProcessor

_DEFAULT_LATENCY_SAMPLE_SIZE = 2000


@dataclass(frozen=True)
class OverviewMetrics:
    """Executive Overview headline numbers for the Phase 7 dashboard.
    Every field is computed directly from the real Phase 4 `detection_
    results` for this run — `detectionLatencyMs` is a live timing
    measurement (see `measure_detection_latency`), not a stored or
    fabricated figure, so it will vary slightly between export runs the
    same way Phase 8's streaming/scalability benchmarks do.
    """

    total_events: int
    anomalies: int
    critical_alerts: int
    detection_accuracy: float
    average_risk: float
    false_positive_rate: float
    detection_latency_ms: float
    measurement_note: str

    def to_dict(self) -> dict[str, object]:
        # camelCase keys: this is the frontend/TypeScript contract
        # (frontend/src/types/dashboard.ts OverviewMetrics), not this
        # project's usual snake_case internal output.
        return {
            "totalEvents": self.total_events,
            "anomalies": self.anomalies,
            "criticalAlerts": self.critical_alerts,
            "detectionAccuracy": self.detection_accuracy,
            "averageRisk": self.average_risk,
            "falsePositiveRate": self.false_positive_rate,
            "detectionLatencyMs": self.detection_latency_ms,
            "measurementNote": self.measurement_note,
        }


def measure_detection_latency(
    *,
    engineered_events_path: Path,
    profile_store_dir: Path,
    sample_size: int = _DEFAULT_LATENCY_SAMPLE_SIZE,
) -> tuple[float, int]:
    """Times the real, unmodified Phase 4 pipeline
    (`StreamProcessor.process_event`) over the first `sample_size` real
    engineered events, against the real profile store. Returns
    (avg_latency_ms, events_measured). This is a genuine wall-clock
    measurement, not a stored or estimated figure — it will vary slightly
    run to run, same as Phase 8's streaming/scalability benchmarks.
    """
    config = DetectionEngineConfig(engineered_events_path=engineered_events_path, profile_store_dir=profile_store_dir)
    engine = build_detection_engine(config)
    processor = StreamProcessor(engine)

    sample_events = pd.read_parquet(engineered_events_path).head(sample_size)
    sample_events["timestamp"] = pd.to_datetime(sample_events["timestamp"], format="ISO8601")

    start = time.perf_counter()
    for row in sample_events.itertuples(index=False):
        event = event_record_from_row(row)
        processor.process_event(event)
    elapsed = time.perf_counter() - start

    measured = len(sample_events)
    avg_latency_ms = (elapsed / measured * 1000) if measured else 0.0
    return avg_latency_ms, measured


def build_overview(
    detection_df: pd.DataFrame,
    *,
    engineered_events_path: Path,
    profile_store_dir: Path,
    latency_sample_size: int = _DEFAULT_LATENCY_SAMPLE_SIZE,
) -> OverviewMetrics:
    total_events = len(detection_df)
    flagged = detection_df[detection_df["verdict"] != "normal"]
    anomalies = len(flagged)
    critical_alerts = int((flagged["severity"] == "critical").sum())

    labeled = detection_df[detection_df["is_attack"].notna()]
    is_attack = labeled["is_attack"].astype(bool)
    flagged_mask = labeled["verdict"] != "normal"
    true_positive = int((is_attack & flagged_mask).sum())
    true_negative = int((~is_attack & ~flagged_mask).sum())
    false_positive = int((~is_attack & flagged_mask).sum())
    accuracy = (true_positive + true_negative) / len(labeled) if len(labeled) else 0.0
    false_positive_rate = false_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0

    average_risk = float(flagged["risk_score"].mean()) if len(flagged) else 0.0

    avg_latency_ms, measured = measure_detection_latency(
        engineered_events_path=engineered_events_path,
        profile_store_dir=profile_store_dir,
        sample_size=latency_sample_size,
    )

    return OverviewMetrics(
        total_events=total_events,
        anomalies=anomalies,
        critical_alerts=critical_alerts,
        detection_accuracy=round(accuracy * 100, 2),
        average_risk=round(average_risk, 2),
        false_positive_rate=round(false_positive_rate * 100, 2),
        detection_latency_ms=round(avg_latency_ms, 3),
        measurement_note=(
            f"Latency measured live over {measured:,} events through the unmodified Phase 4 "
            "DetectionEngine/StreamProcessor against the real profile store."
        ),
    )