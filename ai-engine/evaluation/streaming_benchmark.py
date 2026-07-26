from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from detection.detection_engine import DetectionEngineConfig, build_detection_engine
from detection.profile_comparator import event_record_from_row
from detection.stream_processor import StreamProcessor


@dataclass(frozen=True)
class StreamingBenchmarkResult:
    """Real, per-event-timed throughput of the unmodified Phase 4
    streaming pipeline (`StreamProcessor.process_event`) against the real
    profile store — no synthetic data, no batching shortcuts.
    """

    event_count: int
    total_seconds: float
    events_per_second: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    worst_latency_ms: float

    def to_dict(self) -> dict[str, object]:
        return {
            "event_count": self.event_count,
            "total_seconds": self.total_seconds,
            "events_per_second": self.events_per_second,
            "avg_latency_ms": self.avg_latency_ms,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "worst_latency_ms": self.worst_latency_ms,
        }


class StreamingBenchmark:
    """Replays real engineered events through the real, unmodified
    `StreamProcessor`, timing every individual `process_event` call — the
    exact code path a live event feed would use, per Phase 4's own
    streaming-readiness design.
    """

    def run(
        self,
        *,
        engineered_events_path: Path,
        profile_store_dir: Path,
        sample_size: int | None = None,
        seed: int = 42,
    ) -> StreamingBenchmarkResult:
        events_df = (
            pd.read_parquet(engineered_events_path)
            if engineered_events_path.suffix == ".parquet"
            else pd.read_csv(engineered_events_path, low_memory=False)
        )
        events_df["timestamp"] = pd.to_datetime(events_df["timestamp"], format="ISO8601")

        if sample_size is not None and sample_size < len(events_df):
            sampled_entities = (
                events_df[["entity_id"]].drop_duplicates()["entity_id"].sample(frac=1.0, random_state=seed)
            )
            keep_entities: set[str] = set()
            running_total = 0
            entity_counts = events_df["entity_id"].value_counts()
            for entity_id in sampled_entities:
                keep_entities.add(entity_id)
                running_total += int(entity_counts[entity_id])
                if running_total >= sample_size:
                    break
            events_df = events_df[events_df["entity_id"].isin(keep_entities)]

        events_sorted = events_df.sort_values(["entity_id", "timestamp"], kind="stable").reset_index(drop=True)

        config = DetectionEngineConfig(engineered_events_path=engineered_events_path, profile_store_dir=profile_store_dir)
        engine = build_detection_engine(config)
        processor = StreamProcessor(engine)

        latencies_ms: list[float] = []
        wall_start = time.perf_counter()
        for row in events_sorted.itertuples(index=False):
            event = event_record_from_row(row)
            event_start = time.perf_counter()
            processor.process_event(event)
            latencies_ms.append((time.perf_counter() - event_start) * 1000)
        total_seconds = time.perf_counter() - wall_start

        latency_array = np.array(latencies_ms, dtype=float)
        event_count = len(latency_array)
        events_per_second = event_count / total_seconds if total_seconds > 0 else 0.0

        return StreamingBenchmarkResult(
            event_count=event_count,
            total_seconds=round(total_seconds, 4),
            events_per_second=round(events_per_second, 2),
            avg_latency_ms=round(float(latency_array.mean()), 5) if event_count else 0.0,
            p50_latency_ms=round(float(np.percentile(latency_array, 50)), 5) if event_count else 0.0,
            p95_latency_ms=round(float(np.percentile(latency_array, 95)), 5) if event_count else 0.0,
            p99_latency_ms=round(float(np.percentile(latency_array, 99)), 5) if event_count else 0.0,
            worst_latency_ms=round(float(latency_array.max()), 5) if event_count else 0.0,
        )