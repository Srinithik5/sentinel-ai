from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from evaluation.classification_metrics import ClassificationEvaluator, load_classification_results
from evaluation.cold_start_evaluator import ColdStartEvaluator, build_cold_start_input
from evaluation.concept_drift_evaluator import ConceptDriftEvaluator
from evaluation.detection_metrics import DetectionEvaluator, load_detection_results
from evaluation.latency_benchmark import DashboardLatencyBenchmark
from evaluation.report_generator import EvaluationBundle, ReportGenerator
from evaluation.scalability_benchmark import ScalabilityBenchmark
from evaluation.streaming_benchmark import StreamingBenchmark
from profiles.profile_storage import ProfileStorage

_DEFAULT_ENTITY_COUNTS: tuple[int, ...] = (10, 100, 1_000, 5_000, 10_000, 50_000)


@dataclass(frozen=True)
class EvaluationEngineConfig:
    detection_results_path: Path
    classification_results_path: Path
    engineered_events_path: Path
    profile_store_dir: Path
    frontend_data_dir: Path
    output_dir: Path = field(default_factory=lambda: Path("data/evaluation"))
    scalability_entity_counts: tuple[int, ...] = _DEFAULT_ENTITY_COUNTS
    scalability_events_per_entity: int = 10
    streaming_sample_size: int | None = None
    top_percentile: float = 1.0


class EvaluationEngine:
    """Coordinates the complete Phase 8 evaluation workflow: detection
    evaluation, classification evaluation, cold-start evaluation, concept
    drift evaluation, scalability benchmarking, streaming benchmarking,
    and dashboard latency benchmarking — then hands everything to
    `ReportGenerator` for assembly. Every sub-evaluator is independent and
    individually unit-testable; this class only wires them together.
    """

    def __init__(self, config: EvaluationEngineConfig) -> None:
        self.config = config
        self.detection_evaluator = DetectionEvaluator(top_percentile=config.top_percentile)
        self.classification_evaluator = ClassificationEvaluator()
        self.cold_start_evaluator = ColdStartEvaluator()
        self.concept_drift_evaluator = ConceptDriftEvaluator()
        self.streaming_benchmark = StreamingBenchmark()
        self.dashboard_latency_benchmark = DashboardLatencyBenchmark()
        self.report_generator = ReportGenerator()

    def run(self) -> EvaluationBundle:
        detection_df = load_detection_results(self.config.detection_results_path)
        classification_df = load_classification_results(self.config.classification_results_path)

        import pandas as pd

        events_df = (
            pd.read_parquet(self.config.engineered_events_path)
            if self.config.engineered_events_path.suffix == ".parquet"
            else pd.read_csv(self.config.engineered_events_path, low_memory=False)
        )

        detection_result = self.detection_evaluator.evaluate(detection_df)
        classification_result = self.classification_evaluator.evaluate(classification_df)

        cold_start_input = build_cold_start_input(detection_df, events_df)
        cold_start_result = self.cold_start_evaluator.evaluate(cold_start_input)

        profile_store = ProfileStorage(self.config.profile_store_dir)
        concept_drift_result = self.concept_drift_evaluator.evaluate(events_df, detection_df, profile_store)

        scalability_benchmark = ScalabilityBenchmark(
            engineered_events_path=self.config.engineered_events_path,
            profile_store_dir=self.config.profile_store_dir,
            events_per_entity=self.config.scalability_events_per_entity,
        )
        scalability_result = scalability_benchmark.run(self.config.scalability_entity_counts)

        streaming_result = self.streaming_benchmark.run(
            engineered_events_path=self.config.engineered_events_path,
            profile_store_dir=self.config.profile_store_dir,
            sample_size=self.config.streaming_sample_size,
        )

        dashboard_latency_result = self.dashboard_latency_benchmark.run(self.config.frontend_data_dir)

        from validators.evaluation_validators import run_all_evaluation_validations

        validation = run_all_evaluation_validations(
            detection=detection_result,
            classification=classification_result,
            cold_start=cold_start_result,
            concept_drift=concept_drift_result,
            scalability=scalability_result,
            streaming=streaming_result,
            dashboard_latency=dashboard_latency_result,
        )

        run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        return self.report_generator.build_bundle(
            run_id=run_id,
            detection=detection_result,
            classification=classification_result,
            cold_start=cold_start_result,
            concept_drift=concept_drift_result,
            scalability=scalability_result,
            streaming=streaming_result,
            dashboard_latency=dashboard_latency_result,
            validation=validation,
        )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the SentinelAI Enterprise Evaluation Framework.")
    parser.add_argument("--detection-results", type=Path, required=True, help="Path to detection_results.csv/.parquet (a Phase 4 run).")
    parser.add_argument("--classification-results", type=Path, required=True, help="Path to classification_report.csv/.parquet (a Phase 5 run).")
    parser.add_argument("--events", type=Path, required=True, help="Path to engineered_events.csv/.parquet (a Phase 2C run).")
    parser.add_argument("--profile-store", type=Path, required=True, help="Path to the Phase 3 profile store directory.")
    parser.add_argument("--frontend-data-dir", type=Path, required=True, help="Path to frontend/public/data (a Phase 7 export).")
    parser.add_argument("--output-dir", type=Path, default=Path("data/evaluation"))
    parser.add_argument(
        "--scalability-entity-counts",
        type=int,
        nargs="+",
        default=list(_DEFAULT_ENTITY_COUNTS),
        help="Entity-count tiers for the scalability benchmark.",
    )
    parser.add_argument("--scalability-events-per-entity", type=int, default=10)
    parser.add_argument("--streaming-sample-size", type=int, default=None, help="Limit the streaming benchmark to this many events (default: full dataset).")
    parser.add_argument("--top-percentile", type=float, default=1.0)
    return parser


def main() -> None:
    from outputs.evaluation_writers import (
        write_benchmark_summary,
        write_cold_start_report,
        write_concept_drift_report,
        write_evaluation_report,
        write_metrics_report,
        write_scalability_report,
        write_validation_report,
    )

    args = build_arg_parser().parse_args()
    config = EvaluationEngineConfig(
        detection_results_path=args.detection_results,
        classification_results_path=args.classification_results,
        engineered_events_path=args.events,
        profile_store_dir=args.profile_store,
        frontend_data_dir=args.frontend_data_dir,
        output_dir=args.output_dir,
        scalability_entity_counts=tuple(args.scalability_entity_counts),
        scalability_events_per_entity=args.scalability_events_per_entity,
        streaming_sample_size=args.streaming_sample_size,
        top_percentile=args.top_percentile,
    )

    print("Running Enterprise Evaluation Framework...")
    engine = EvaluationEngine(config)
    bundle = engine.run()

    print(f"Detection: precision={bundle.detection.confusion.precision:.4f} recall={bundle.detection.confusion.recall:.4f} "
          f"f1={bundle.detection.confusion.f1:.4f} roc_auc={bundle.detection.roc.auc:.4f} pr_auc={bundle.detection.pr.auc:.4f}")
    print(f"Classification: macro_f1={bundle.classification.macro_f1:.4f} weighted_f1={bundle.classification.weighted_f1:.4f} "
          f"accuracy={bundle.classification.overall_accuracy:.4f}")
    print(f"Streaming: {bundle.streaming.events_per_second:,.1f} events/sec, "
          f"avg={bundle.streaming.avg_latency_ms:.4f}ms worst={bundle.streaming.worst_latency_ms:.4f}ms")

    run_dir = config.output_dir / bundle.run_id
    write_evaluation_report(bundle, run_dir / "evaluation_report.md")
    write_metrics_report(bundle, run_dir / "metrics_report.md")
    write_scalability_report(bundle, run_dir / "scalability_report.md")
    write_cold_start_report(bundle, run_dir / "cold_start_report.md")
    write_concept_drift_report(bundle, run_dir / "concept_drift_report.md")
    write_benchmark_summary(bundle, run_dir / "benchmark_summary.md")
    write_validation_report(bundle, run_dir / "evaluation_validation_report.md")

    print(
        f"Validation: {'PASSED' if bundle.validation.passed else 'FAILED'} "
        f"({bundle.validation.error_count} errors, {bundle.validation.warning_count} warnings)"
    )
    print(f"Output written to: {run_dir.resolve()}")

    if not bundle.validation.passed:
        raise RuntimeError(
            f"Evaluation validation failed with {bundle.validation.error_count} error(s). "
            f"See {run_dir / 'evaluation_validation_report.md'} for details."
        )


if __name__ == "__main__":
    main()