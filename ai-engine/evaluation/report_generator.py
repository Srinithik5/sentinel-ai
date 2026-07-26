from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from evaluation.classification_metrics import ClassificationEvaluationResult
from evaluation.cold_start_evaluator import ColdStartEvaluationResult
from evaluation.concept_drift_evaluator import ConceptDriftEvaluationResult
from evaluation.detection_metrics import DetectionEvaluationResult
from evaluation.latency_benchmark import DashboardLatencyBenchmarkResult
from evaluation.scalability_benchmark import ScalabilityBenchmarkResult
from evaluation.streaming_benchmark import StreamingBenchmarkResult
from validators.evaluation_validators import ValidationReport


@dataclass(frozen=True)
class EvaluationBundle:
    """The complete Phase 8 output for one evaluation run: every
    evaluator's result plus the validation outcome, timestamped and
    identified by a single run ID — the one object `outputs/
    evaluation_writers.py` renders into the six required reports.
    """

    run_id: str
    generated_at: str
    detection: DetectionEvaluationResult
    classification: ClassificationEvaluationResult
    cold_start: ColdStartEvaluationResult
    concept_drift: ConceptDriftEvaluationResult
    scalability: ScalabilityBenchmarkResult
    streaming: StreamingBenchmarkResult
    dashboard_latency: DashboardLatencyBenchmarkResult
    validation: ValidationReport

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "generated_at": self.generated_at,
            "detection": self.detection.to_dict(),
            "classification": self.classification.to_dict(),
            "cold_start": self.cold_start.to_dict(),
            "concept_drift": self.concept_drift.to_dict(),
            "scalability": self.scalability.to_dict(),
            "streaming": self.streaming.to_dict(),
            "dashboard_latency": self.dashboard_latency.to_dict(),
            "validation": {
                "passed": self.validation.passed,
                "error_count": self.validation.error_count,
                "warning_count": self.validation.warning_count,
            },
        }


class ReportGenerator:
    """Assembles every evaluator's output into one timestamped
    EvaluationBundle. Pure aggregation — no metric computation happens
    here, only packaging of results already computed by the individual
    evaluators/benchmarks.
    """

    def build_bundle(
        self,
        *,
        run_id: str,
        detection: DetectionEvaluationResult,
        classification: ClassificationEvaluationResult,
        cold_start: ColdStartEvaluationResult,
        concept_drift: ConceptDriftEvaluationResult,
        scalability: ScalabilityBenchmarkResult,
        streaming: StreamingBenchmarkResult,
        dashboard_latency: DashboardLatencyBenchmarkResult,
        validation: ValidationReport,
    ) -> EvaluationBundle:
        return EvaluationBundle(
            run_id=run_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            detection=detection,
            classification=classification,
            cold_start=cold_start,
            concept_drift=concept_drift,
            scalability=scalability,
            streaming=streaming,
            dashboard_latency=dashboard_latency,
            validation=validation,
        )