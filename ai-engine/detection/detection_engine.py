from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path

import pandas as pd

from detection.anomaly_scorer import AnomalyScorer, build_scoring_strategy
from detection.decision_engine import DecisionEngine, DetectionVerdict
from detection.profile_comparator import DimensionDeviation, EventRecord, ProfileComparator, event_record_from_row
from detection.risk_engine import RiskAssessment, RiskEngine, RiskEngineConfig
from detection.threshold_manager import SeverityLevel, ThresholdConfig, ThresholdManager
from profiles.profile_storage import ProfileStorage


@dataclass(frozen=True)
class DetectionResult:
    event_id: str
    entity_id: str
    timestamp: datetime
    entity_type: str | None
    dimension_deviations: tuple[DimensionDeviation, ...]
    anomaly_score: float
    risk_assessment: RiskAssessment
    severity: SeverityLevel
    verdict: DetectionVerdict
    scoring_strategy: str
    profile_version: int | None
    is_attack: bool | None = None

    def to_dict(self) -> dict[str, object]:
        row: dict[str, object] = {
            "event_id": self.event_id,
            "entity_id": self.entity_id,
            "timestamp": self.timestamp.isoformat(),
            "entity_type": self.entity_type,
            "anomaly_score": self.anomaly_score,
            "risk_score": self.risk_assessment.risk_score,
            "severity": self.severity.value,
            "verdict": self.verdict.value,
            "scoring_strategy": self.scoring_strategy,
            "profile_version": self.profile_version,
            "is_attack": self.is_attack,
        }
        for deviation in self.dimension_deviations:
            row[f"deviation_{deviation.dimension}"] = deviation.deviation_score
        row.update(
            {
                "risk_deviation_component": self.risk_assessment.deviation_component,
                "risk_indicator_component": self.risk_assessment.indicator_component,
                "risk_confidence_component": self.risk_assessment.confidence_component,
                "risk_trust_component": self.risk_assessment.trust_component,
                "risk_cold_start_component": self.risk_assessment.cold_start_component,
                "historical_confidence": self.risk_assessment.historical_confidence,
                "entity_trust": self.risk_assessment.entity_trust,
            }
        )
        return row


class DetectionEngine:
    """Coordinates the complete anomaly detection workflow for one event:
    compare against the entity's behaviour profile, score the deviations,
    compute a normalized risk score, and decide a verdict. This is the only
    class the rest of the system needs to know about — everything else
    (comparator, scorer, risk engine, thresholds, decisions) is an
    implementation detail wired together here.
    """

    def __init__(
        self,
        *,
        profile_store: ProfileStorage,
        comparator: ProfileComparator,
        scorer: AnomalyScorer,
        risk_engine: RiskEngine,
        threshold_manager: ThresholdManager,
        decision_engine: DecisionEngine,
    ) -> None:
        self.profile_store = profile_store
        self.comparator = comparator
        self.scorer = scorer
        self.risk_engine = risk_engine
        self.threshold_manager = threshold_manager
        self.decision_engine = decision_engine
        self._profile_cache: dict[str, object] = {}

    def detect(self, event: EventRecord, *, previous_resource: str | None = None) -> DetectionResult:
        profile = self._get_profile(event.entity_id)
        deviations = self.comparator.compare(event, profile, previous_resource=previous_resource)
        anomaly_score = self.scorer.compute_score(deviations)
        risk_assessment = self.risk_engine.compute_risk(event=event, profile=profile, anomaly_score=anomaly_score)
        severity = self.threshold_manager.severity_for(risk_assessment.risk_score)
        verdict = self.decision_engine.decide(risk_assessment.risk_score)

        return DetectionResult(
            event_id=event.event_id,
            entity_id=event.entity_id,
            timestamp=event.timestamp,
            entity_type=profile.entity_type if profile is not None else None,
            dimension_deviations=deviations,
            anomaly_score=anomaly_score,
            risk_assessment=risk_assessment,
            severity=severity,
            verdict=verdict,
            scoring_strategy=self.scorer.strategy.name,
            profile_version=profile.version if profile is not None else None,
        )

    def _get_profile(self, entity_id: str):
        if entity_id not in self._profile_cache:
            self._profile_cache[entity_id] = self.profile_store.load_latest(entity_id)
        return self._profile_cache[entity_id]


@dataclass(frozen=True)
class DetectionEngineConfig:
    engineered_events_path: Path
    profile_store_dir: Path
    output_dir: Path = field(default_factory=lambda: Path("data/detections"))
    scoring_strategy: str = "weighted_average"
    threshold_config: ThresholdConfig = field(default_factory=ThresholdConfig)
    risk_config: RiskEngineConfig = field(default_factory=RiskEngineConfig)


def build_detection_engine(config: DetectionEngineConfig) -> DetectionEngine:
    return DetectionEngine(
        profile_store=ProfileStorage(config.profile_store_dir),
        comparator=ProfileComparator(),
        scorer=AnomalyScorer(build_scoring_strategy(config.scoring_strategy)),
        risk_engine=RiskEngine(config.risk_config),
        threshold_manager=ThresholdManager(config.threshold_config),
        decision_engine=DecisionEngine(ThresholdManager(config.threshold_config)),
    )


def _load_events(path: Path) -> pd.DataFrame:
    events_df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, low_memory=False)
    events_df["timestamp"] = pd.to_datetime(events_df["timestamp"], format="ISO8601")
    return events_df


def run_detection(config: DetectionEngineConfig) -> list[DetectionResult]:
    """Runs detection over every event in the input file, in chronological
    order per entity — deliberately including attack-labeled events, since
    detecting them is the entire point. Ground truth (`is_attack`), when
    present, is attached to each result only AFTER detection completes; it
    is never read by any component that produces the score or verdict.
    """
    from detection.stream_processor import StreamProcessor  # deferred: avoids a circular import with this module

    events_df = _load_events(config.engineered_events_path)
    events_sorted = events_df.sort_values(["entity_id", "timestamp"], kind="stable").reset_index(drop=True)
    has_ground_truth = "is_attack" in events_sorted.columns

    engine = build_detection_engine(config)
    processor = StreamProcessor(engine)

    results: list[DetectionResult] = []
    for row in events_sorted.itertuples(index=False):
        event = event_record_from_row(row)
        result = processor.process_event(event)
        if has_ground_truth:
            result = replace(result, is_attack=bool(row.is_attack))
        results.append(result)
    return results


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run SentinelAI behavioural anomaly detection over engineered events.")
    parser.add_argument("--events", type=Path, required=True, help="Path to engineered_events.csv or .parquet (a Phase 2C run).")
    parser.add_argument("--profile-store", type=Path, required=True, help="Path to the Phase 3 profile store directory.")
    parser.add_argument("--output-dir", type=Path, default=Path("data/detections"))
    parser.add_argument(
        "--scoring-strategy", type=str, default="weighted_average", choices=["weighted_average", "max_deviation"]
    )
    return parser


def main() -> None:
    from outputs.detection_writers import (
        write_detection_metrics,
        write_detection_results,
        write_detection_summary,
        write_risk_score_report,
        write_validation_report,
    )
    from validators.detection_validators import run_all_detection_validations

    args = build_arg_parser().parse_args()
    config = DetectionEngineConfig(
        engineered_events_path=args.events,
        profile_store_dir=args.profile_store,
        output_dir=args.output_dir,
        scoring_strategy=args.scoring_strategy,
    )

    print(f"Loading engineered events from: {config.engineered_events_path}")
    print(f"Loading profile store from: {config.profile_store_dir}")
    results = run_detection(config)
    print(f"Scored {len(results):,} events using the '{config.scoring_strategy}' strategy.")

    verdict_counts = Counter(result.verdict for result in results)
    print(
        f"Verdicts: normal={verdict_counts.get(DetectionVerdict.NORMAL, 0):,} "
        f"suspicious={verdict_counts.get(DetectionVerdict.SUSPICIOUS, 0):,} "
        f"anomalous={verdict_counts.get(DetectionVerdict.ANOMALOUS, 0):,}"
    )

    threshold_manager = ThresholdManager(config.threshold_config)
    decision_engine = DecisionEngine(threshold_manager)
    validation_report = run_all_detection_validations(
        results, threshold_manager=threshold_manager, decision_engine=decision_engine
    )

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = config.output_dir / run_id

    write_detection_results(results, run_dir / "detection_results.csv", run_dir / "detection_results.parquet")
    write_risk_score_report(results, run_dir / "risk_score_report.md")
    write_detection_summary(results, run_dir / "detection_summary.md")
    write_detection_metrics(results, run_dir / "detection_metrics.md")
    write_validation_report(validation_report, run_dir / "detection_validation_report.md")

    print(
        f"Validation: {'PASSED' if validation_report.passed else 'FAILED'} "
        f"({validation_report.error_count} errors, {validation_report.warning_count} warnings)"
    )
    print(f"Output written to: {run_dir.resolve()}")

    if not validation_report.passed:
        raise RuntimeError(
            f"Detection validation failed with {validation_report.error_count} error(s). "
            f"See {run_dir / 'detection_validation_report.md'} for details."
        )


if __name__ == "__main__":
    main()