from __future__ import annotations

import random
import time
import tracemalloc
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

import pandas as pd

from detection.anomaly_scorer import AnomalyScorer, build_scoring_strategy
from detection.decision_engine import DecisionEngine
from detection.detection_engine import DetectionEngine
from detection.profile_comparator import EventRecord, ProfileComparator, event_record_from_row
from detection.risk_engine import RiskEngine, RiskEngineConfig
from detection.stream_processor import StreamProcessor
from detection.threshold_manager import ThresholdConfig, ThresholdManager
from profiles.profile_manager import BehaviourProfile
from profiles.profile_storage import ProfileStorage

_DEFAULT_ENTITY_COUNTS: tuple[int, ...] = (10, 100, 1_000, 5_000, 10_000, 50_000)
_DEFAULT_EVENTS_PER_ENTITY = 10
_DEFAULT_SAMPLE_POOL_SIZE = 8_000


@dataclass(frozen=True)
class ScalabilityTierResult:
    """Measured cost of running the real, unmodified DetectionEngine over
    one entity-count tier. `real_entity_count` entities use their actual
    Phase 2C event history and Phase 3 profile; any remainder up to
    `target_entity_count` is synthetically cloned from real profiles/
    events (see ScalabilityBenchmark's class docstring) purely to reach
    volumes beyond the real dataset's 2,500 entities for load testing.
    """

    target_entity_count: int
    real_entity_count: int
    synthetic_entity_count: int
    event_count: int
    total_seconds: float
    avg_latency_ms: float
    peak_memory_mb: float
    cpu_seconds: float
    throughput_events_per_sec: float

    def to_dict(self) -> dict[str, object]:
        return {
            "target_entity_count": self.target_entity_count,
            "real_entity_count": self.real_entity_count,
            "synthetic_entity_count": self.synthetic_entity_count,
            "event_count": self.event_count,
            "total_seconds": self.total_seconds,
            "avg_latency_ms": self.avg_latency_ms,
            "peak_memory_mb": self.peak_memory_mb,
            "cpu_seconds": self.cpu_seconds,
            "throughput_events_per_sec": self.throughput_events_per_sec,
        }


@dataclass(frozen=True)
class ScalabilityBenchmarkResult:
    events_per_entity: int
    tiers: tuple[ScalabilityTierResult, ...]
    methodology_note: str

    def to_dict(self) -> dict[str, object]:
        return {
            "events_per_entity": self.events_per_entity,
            "methodology_note": self.methodology_note,
            "tiers": [tier.to_dict() for tier in self.tiers],
        }


class InMemoryProfileStore:
    """A minimal, duck-typed stand-in for `profiles.profile_storage.
    ProfileStorage` — implements only the one method `DetectionEngine`
    actually calls (`load_latest`), backed by an in-memory dict instead of
    disk. Used here so scaling to tens of thousands of entities never
    touches the filesystem, keeping the benchmark measuring detection
    compute cost rather than incidental I/O cost.
    """

    def __init__(self, profiles: dict[str, BehaviourProfile]) -> None:
        self._profiles = profiles

    def load_latest(self, entity_id: str) -> BehaviourProfile | None:
        return self._profiles.get(entity_id)


def _build_detection_engine(profile_store: InMemoryProfileStore) -> DetectionEngine:
    threshold_manager = ThresholdManager(ThresholdConfig())
    return DetectionEngine(
        profile_store=profile_store,
        comparator=ProfileComparator(),
        scorer=AnomalyScorer(build_scoring_strategy("weighted_average")),
        risk_engine=RiskEngine(RiskEngineConfig()),
        threshold_manager=threshold_manager,
        decision_engine=DecisionEngine(threshold_manager),
    )


class ScalabilityBenchmark:
    """Benchmarks the real, unmodified Phase 4 detection pipeline
    (`ProfileComparator` -> `AnomalyScorer` -> `RiskEngine` ->
    `ThresholdManager` -> `DecisionEngine`, driven through the real
    `StreamProcessor`) across increasing entity counts.

    The real dataset has 2,500 entities. Tiers at or below that use only
    real entities, each replaying a real sample of its own event history
    against its real Phase 3 profile. Tiers above 2,500 (the spec asks for
    up to 50,000) extend the real entity set with synthetic entities: each
    synthetic entity's profile is a real profile cloned under a new ID
    (`dataclasses.replace`, no new profile is invented), and each
    synthetic event is a real event row cloned under a new entity/event ID
    (feature values are real, only identity fields change). This is a
    standard, honest load-testing technique — scaling real traffic
    patterns up in volume — and is never used for accuracy evaluation,
    only for measuring how latency/memory/CPU/throughput scale with
    entity count.
    """

    def __init__(
        self,
        *,
        engineered_events_path: Path,
        profile_store_dir: Path,
        events_per_entity: int = _DEFAULT_EVENTS_PER_ENTITY,
        sample_pool_size: int = _DEFAULT_SAMPLE_POOL_SIZE,
        seed: int = 42,
    ) -> None:
        self.events_per_entity = events_per_entity
        self._rng = random.Random(seed)

        events_df = (
            pd.read_parquet(engineered_events_path)
            if engineered_events_path.suffix == ".parquet"
            else pd.read_csv(engineered_events_path, low_memory=False)
        )
        events_df["timestamp"] = pd.to_datetime(events_df["timestamp"], format="ISO8601")

        self._real_entity_ids: list[str] = sorted(events_df["entity_id"].unique())

        profile_store = ProfileStorage(profile_store_dir)
        self._real_profiles: dict[str, BehaviourProfile] = {}
        for entity_id in self._real_entity_ids:
            profile = profile_store.load_latest(entity_id)
            if profile is not None:
                self._real_profiles[entity_id] = profile

        self._events_by_entity: dict[str, list[EventRecord]] = {}
        for row in events_df.itertuples(index=False):
            record = event_record_from_row(row)
            self._events_by_entity.setdefault(record.entity_id, []).append(record)

        pool_size = min(sample_pool_size, len(events_df))
        sample_rows = events_df.sample(n=pool_size, random_state=seed)
        self._event_pool: list[EventRecord] = [event_record_from_row(row) for row in sample_rows.itertuples(index=False)]

    def run(self, entity_counts: Sequence[int] = _DEFAULT_ENTITY_COUNTS) -> ScalabilityBenchmarkResult:
        tiers = tuple(self._run_tier(target) for target in entity_counts)
        note = (
            f"Real dataset provides {len(self._real_entity_ids):,} real entities with real event history and "
            f"real Phase 3 profiles. Tiers above that count extend the entity set with synthetic entities built "
            f"from real profiles/events cloned under new IDs (see class docstring) — load-testing only, not an "
            f"accuracy measurement. Every tier replays {self.events_per_entity} events per entity."
        )
        return ScalabilityBenchmarkResult(events_per_entity=self.events_per_entity, tiers=tiers, methodology_note=note)

    def _run_tier(self, target_entity_count: int) -> ScalabilityTierResult:
        real_ids = self._real_entity_ids[: min(target_entity_count, len(self._real_entity_ids))]
        synthetic_count = max(0, target_entity_count - len(self._real_entity_ids))

        profiles: dict[str, BehaviourProfile] = {}
        entity_events: list[EventRecord] = []

        for entity_id in real_ids:
            profile = self._real_profiles.get(entity_id)
            if profile is not None:
                profiles[entity_id] = profile
            entity_events.extend(self._sample_events_for_entity(entity_id, self.events_per_entity))

        for index in range(synthetic_count):
            synthetic_id = f"SYN-{index:07d}"
            source_id = self._real_entity_ids[index % len(self._real_entity_ids)]
            source_profile = self._real_profiles.get(source_id)
            if source_profile is not None:
                profiles[synthetic_id] = replace(source_profile, entity_id=synthetic_id)

            for event_index in range(self.events_per_entity):
                base_event = self._event_pool[self._rng.randrange(len(self._event_pool))]
                entity_events.append(
                    replace(base_event, event_id=f"synth-{synthetic_id}-{event_index}", entity_id=synthetic_id)
                )

        entity_events.sort(key=lambda event: (event.entity_id, event.timestamp))

        engine = _build_detection_engine(InMemoryProfileStore(profiles))
        processor = StreamProcessor(engine)

        tracemalloc.start()
        cpu_start = time.process_time()
        wall_start = time.perf_counter()
        for event in entity_events:
            processor.process_event(event)
        wall_elapsed = time.perf_counter() - wall_start
        cpu_elapsed = time.process_time() - cpu_start
        _current_bytes, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        event_count = len(entity_events)
        avg_latency_ms = (wall_elapsed / event_count * 1000) if event_count else 0.0
        throughput = (event_count / wall_elapsed) if wall_elapsed > 0 else 0.0

        return ScalabilityTierResult(
            target_entity_count=target_entity_count,
            real_entity_count=len(real_ids),
            synthetic_entity_count=synthetic_count,
            event_count=event_count,
            total_seconds=round(wall_elapsed, 4),
            avg_latency_ms=round(avg_latency_ms, 4),
            peak_memory_mb=round(peak_bytes / (1024 * 1024), 4),
            cpu_seconds=round(cpu_elapsed, 4),
            throughput_events_per_sec=round(throughput, 2),
        )

    def _sample_events_for_entity(self, entity_id: str, count: int) -> list[EventRecord]:
        pool = self._events_by_entity.get(entity_id, [])
        if not pool:
            return []
        if len(pool) >= count:
            return self._rng.sample(pool, count)
        return [pool[i % len(pool)] for i in range(count)]