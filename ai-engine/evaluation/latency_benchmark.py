from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_FIXTURE_NAMES: tuple[str, ...] = ("overview.json", "alerts.json", "analytics.json", "mitre.json", "system_health.json")
_SEARCH_QUERY_REPEATS = 200


@dataclass(frozen=True)
class DataLoadLatencyResult:
    """A real proxy for "Dashboard API latency": the time to read and
    JSON-parse the actual static fixture the Phase 7 dashboard's
    `dashboard.service.ts` fetches — the same payload, the same
    deserialization cost, measured server-side in Python rather than in
    the browser.
    """

    fixture_name: str
    payload_bytes: int
    read_seconds: float
    parse_seconds: float

    def to_dict(self) -> dict[str, object]:
        return {
            "fixture_name": self.fixture_name,
            "payload_bytes": self.payload_bytes,
            "read_seconds": self.read_seconds,
            "parse_seconds": self.parse_seconds,
        }


@dataclass(frozen=True)
class SearchLatencyResult:
    """Real timing of the exact search predicate the Phase 7 `AlertQueue`
    component uses (substring match across entity ID, event ID, attack
    display name, and MITRE technique), re-implemented faithfully here and
    run against the real alerts dataset — a genuine proxy for client-side
    search cost at the same data volume the dashboard actually holds.
    """

    query_count: int
    dataset_size: int
    avg_latency_ms: float
    p95_latency_ms: float
    worst_latency_ms: float

    def to_dict(self) -> dict[str, object]:
        return {
            "query_count": self.query_count,
            "dataset_size": self.dataset_size,
            "avg_latency_ms": self.avg_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "worst_latency_ms": self.worst_latency_ms,
        }


@dataclass(frozen=True)
class RenderProxyResult:
    """NOT a measurement of actual DOM paint/render time — that requires
    browser instrumentation (e.g. the Performance/Paint Timing API), which
    is out of scope for a Python ai-engine benchmark and is not fabricated
    here. This measures JSON re-serialization cost of the same payload as
    a defensible, honestly-labeled proxy for "how much data-shaping work
    stands between the fetched payload and something a UI can render."
    """

    payload_bytes: int
    serialize_seconds: float
    note: str

    def to_dict(self) -> dict[str, object]:
        return {"payload_bytes": self.payload_bytes, "serialize_seconds": self.serialize_seconds, "note": self.note}


@dataclass(frozen=True)
class DashboardLatencyBenchmarkResult:
    api_latency: tuple[DataLoadLatencyResult, ...]
    search_latency: SearchLatencyResult
    render_proxy: RenderProxyResult

    def to_dict(self) -> dict[str, object]:
        return {
            "api_latency": [result.to_dict() for result in self.api_latency],
            "search_latency": self.search_latency.to_dict(),
            "render_proxy": self.render_proxy.to_dict(),
        }


def _matches_query(alert: dict[str, object], query: str) -> bool:
    """The exact predicate `AlertQueue.tsx` uses client-side, ported
    faithfully to Python for benchmarking."""
    haystacks = (
        str(alert.get("entityId", "")),
        str(alert.get("eventId", "")),
        str(alert.get("attackDisplayName", "")),
        str(alert.get("mitreTechnique", "")),
    )
    return any(query in haystack.lower() for haystack in haystacks)


class DashboardLatencyBenchmark:
    """Benchmarks the Phase 7 dashboard's data layer using the actual
    static fixtures it consumes (`frontend/public/data/*.json`) — API
    (data-load) latency, search latency, and an explicitly-labeled
    rendering proxy.
    """

    def run(self, frontend_data_dir: Path, *, seed: int = 42) -> DashboardLatencyBenchmarkResult:
        api_results: list[DataLoadLatencyResult] = []
        alerts_payload: list[dict[str, object]] = []

        for fixture_name in _FIXTURE_NAMES:
            path = frontend_data_dir / fixture_name
            if not path.exists():
                raise FileNotFoundError(f"Dashboard fixture not found: {path}")

            read_start = time.perf_counter()
            raw_bytes = path.read_bytes()
            read_seconds = time.perf_counter() - read_start

            parse_start = time.perf_counter()
            payload = json.loads(raw_bytes)
            parse_seconds = time.perf_counter() - parse_start

            api_results.append(
                DataLoadLatencyResult(
                    fixture_name=fixture_name,
                    payload_bytes=len(raw_bytes),
                    read_seconds=round(read_seconds, 6),
                    parse_seconds=round(parse_seconds, 6),
                )
            )
            if fixture_name == "alerts.json":
                alerts_payload = payload

        search_latency = self._benchmark_search(alerts_payload, seed=seed)
        render_proxy = self._benchmark_render_proxy(alerts_payload)

        return DashboardLatencyBenchmarkResult(
            api_latency=tuple(api_results), search_latency=search_latency, render_proxy=render_proxy
        )

    def _benchmark_search(self, alerts: list[dict[str, object]], *, seed: int) -> SearchLatencyResult:
        import random

        rng = random.Random(seed)
        if not alerts:
            return SearchLatencyResult(0, 0, 0.0, 0.0, 0.0)

        sample_alerts = rng.sample(alerts, min(_SEARCH_QUERY_REPEATS, len(alerts)))
        queries = [str(alert.get("entityId", "")).lower()[:6] for alert in sample_alerts]

        latencies_ms: list[float] = []
        for query in queries:
            start = time.perf_counter()
            [alert for alert in alerts if _matches_query(alert, query)]
            latencies_ms.append((time.perf_counter() - start) * 1000)

        latency_array = np.array(latencies_ms, dtype=float)
        return SearchLatencyResult(
            query_count=len(queries),
            dataset_size=len(alerts),
            avg_latency_ms=round(float(latency_array.mean()), 4),
            p95_latency_ms=round(float(np.percentile(latency_array, 95)), 4),
            worst_latency_ms=round(float(latency_array.max()), 4),
        )

    def _benchmark_render_proxy(self, alerts: list[dict[str, object]]) -> RenderProxyResult:
        start = time.perf_counter()
        serialized = json.dumps(alerts)
        elapsed = time.perf_counter() - start
        return RenderProxyResult(
            payload_bytes=len(serialized.encode("utf-8")),
            serialize_seconds=round(elapsed, 6),
            note=(
                "This is a data-shaping proxy (JSON re-serialization time), not a measurement of actual browser "
                "DOM paint/render time. True rendering latency requires browser-side instrumentation (e.g. the "
                "Performance/Paint Timing API) which is out of scope for this Python-based benchmark and is "
                "intentionally not fabricated here."
            ),
        )