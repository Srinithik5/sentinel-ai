from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_RESULT_LINE = re.compile(r"^Result:\s*(PASSED|FAILED)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class LiveHealthComponent:
    note: str

    def to_dict(self) -> dict[str, object]:
        return {"mode": "live", "note": self.note}


@dataclass(frozen=True)
class BatchHealthComponent:
    """One offline/batch pipeline stage's health, derived from its own
    real run: `last_run_id` is the actual timestamped run directory used,
    `last_run_passed` is read from that run's own `*_validation_report.md`
    (never assumed), and `events_processed` is the real row count of the
    file this export read.
    """

    status: str
    last_run_id: str
    last_run_passed: bool
    events_processed: int
    note: str

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": "batch",
            "status": self.status,
            "lastRunId": self.last_run_id,
            "lastRunPassed": self.last_run_passed,
            "eventsProcessed": self.events_processed,
            "note": self.note,
        }


@dataclass(frozen=True)
class NotDeployedHealthComponent:
    status: str
    note: str

    def to_dict(self) -> dict[str, object]:
        return {"mode": "not_deployed", "status": self.status, "note": self.note}


@dataclass(frozen=True)
class SystemHealthData:
    backend: LiveHealthComponent
    database: LiveHealthComponent
    detection_engine: BatchHealthComponent
    classification_engine: BatchHealthComponent
    explainability_engine: BatchHealthComponent
    streaming_pipeline: NotDeployedHealthComponent

    def to_dict(self) -> dict[str, object]:
        return {
            "backend": self.backend.to_dict(),
            "database": self.database.to_dict(),
            "detectionEngine": self.detection_engine.to_dict(),
            "classificationEngine": self.classification_engine.to_dict(),
            "explainabilityEngine": self.explainability_engine.to_dict(),
            "streamingPipeline": self.streaming_pipeline.to_dict(),
        }


def _read_validation_passed(report_path: Path) -> bool:
    """Reads the real `Result: PASSED`/`Result: FAILED` line every phase's
    validator writes. Raises if the report is missing rather than
    assuming a status — an untested run should never be reported healthy.
    """
    if not report_path.exists():
        raise FileNotFoundError(f"Validation report not found: {report_path}")
    match = _RESULT_LINE.search(report_path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"Could not find a 'Result: PASSED|FAILED' line in {report_path}")
    return match.group(1) == "PASSED"


def build_system_health(
    *,
    detection_results_path: Path,
    detection_event_count: int,
    classification_results_path: Path,
    classification_event_count: int,
    explainability_dir: Path,
    explainability_event_count: int,
) -> SystemHealthData:
    detection_run_id = detection_results_path.parent.name
    classification_run_id = classification_results_path.parent.name
    explainability_run_id = explainability_dir.name

    detection_passed = _read_validation_passed(detection_results_path.parent / "detection_validation_report.md")
    classification_passed = _read_validation_passed(
        classification_results_path.parent / "classification_validation_report.md"
    )
    explainability_passed = _read_validation_passed(explainability_dir / "explainability_validation_report.md")

    return SystemHealthData(
        backend=LiveHealthComponent(note="Polled from GET /api/v1/health in real time by the dashboard."),
        database=LiveHealthComponent(note="Reported by the backend health endpoint alongside backend status."),
        detection_engine=BatchHealthComponent(
            status="operational" if detection_passed else "degraded",
            last_run_id=detection_run_id,
            last_run_passed=detection_passed,
            events_processed=detection_event_count,
            note="Offline CLI pipeline (python -m detection.detection_engine).",
        ),
        classification_engine=BatchHealthComponent(
            status="operational" if classification_passed else "degraded",
            last_run_id=classification_run_id,
            last_run_passed=classification_passed,
            events_processed=classification_event_count,
            note="Offline CLI pipeline (python -m classification.classification_engine).",
        ),
        explainability_engine=BatchHealthComponent(
            status="operational" if explainability_passed else "degraded",
            last_run_id=explainability_run_id,
            last_run_passed=explainability_passed,
            events_processed=explainability_event_count,
            note="Offline CLI pipeline (python -m explainability.explainability_engine).",
        ),
        streaming_pipeline=NotDeployedHealthComponent(
            status="offline",
            note="Real-time/streaming ingestion is not yet implemented; all phases currently run as batch CLI jobs.",
        ),
    )