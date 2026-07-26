from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path

import pandas as pd

from classification.attack_classifier import (
    PRIMARY_DIMENSION,
    AttackClassifier,
    ClassificationScores,
    build_classification_strategy,
)
from classification.attack_registry import AttackType, get_attack_definition
from classification.confidence_engine import ConfidenceEngine, ConfidenceEngineConfig
from classification.evidence_collector import EvidenceBundle, EvidenceCollector
from classification.mitre_mapper import map_attack
from detection.threshold_manager import SeverityLevel
from profiles.profile_manager import BehaviourProfile
from profiles.profile_storage import ProfileStorage

# Engineered-feature columns EvidenceCollector needs, pulled from Phase 2C's
# engineered_events file. Deliberately excludes every Phase 2B ground-truth
# column (attack_type, mitre_tactic, mitre_technique, attack_id, confidence,
# description, injected, is_attack) from this list — those are read
# separately, only to attach `ground_truth_attack_type` AFTER classification.
_FEATURE_COLUMNS: tuple[str, ...] = (
    "event_id",
    "resource_accessed",
    "login_result",
    "consecutive_failures",
    "burst_access_score",
    "mfa_usage_frequency",
    "geo_velocity_kmh",
    "country_change",
    "geo_novelty",
    "device_familiarity_score",
    "fingerprint_mismatch",
    "os_novelty",
    "mac_novelty",
    "resource_novelty",
    "resource_diversity",
    "sensitive_resource_access",
    "privilege_change_indicator",
    "session_entropy",
    "command_sequence_complexity",
    "behaviour_drift_score",
    "historical_percentile_session_duration",
    "history_length",
    "new_entity_flag",
)

_DETECTION_COLUMNS: tuple[str, ...] = (
    "event_id",
    "entity_id",
    "timestamp",
    "entity_type",
    "anomaly_score",
    "risk_score",
    "severity",
    "verdict",
    "deviation_temporal",
    "deviation_device",
    "deviation_resource",
    "deviation_geographic",
    "deviation_authentication",
    "deviation_session",
)

_UNKNOWN_SCORE_FLOOR = 0.4


@dataclass(frozen=True)
class ClassificationResult:
    event_id: str
    entity_id: str
    timestamp: datetime
    entity_type: str | None
    attack_type: AttackType
    display_name: str
    confidence: float
    severity: SeverityLevel
    mitre_tactic: str
    mitre_technique: str
    evidence: tuple[str, ...]
    all_scores: dict[str, float]
    classification_strategy: str
    detection_anomaly_score: float
    detection_risk_score: float
    detection_severity: str
    detection_verdict: str
    ground_truth_attack_type: str | None = None

    def to_dict(self) -> dict[str, object]:
        row: dict[str, object] = {
            "event_id": self.event_id,
            "entity_id": self.entity_id,
            "timestamp": self.timestamp.isoformat(),
            "entity_type": self.entity_type,
            "attack_type": self.attack_type.value,
            "display_name": self.display_name,
            "confidence": self.confidence,
            "severity": self.severity.value,
            "mitre_tactic": self.mitre_tactic,
            "mitre_technique": self.mitre_technique,
            "evidence": " | ".join(self.evidence),
            "classification_strategy": self.classification_strategy,
            "detection_anomaly_score": self.detection_anomaly_score,
            "detection_risk_score": self.detection_risk_score,
            "detection_severity": self.detection_severity,
            "detection_verdict": self.detection_verdict,
            "ground_truth_attack_type": self.ground_truth_attack_type,
        }
        for attack_type, score in self.all_scores.items():
            row[f"score_{attack_type}"] = score
        return row


class ClassificationEngine:
    """Coordinates the complete attack classification workflow for one
    already-flagged event: score every known attack type against the
    evidence, pick a winner (or UNKNOWN if nothing scored highly enough),
    compute a confidence score, and resolve its MITRE mapping. Mirrors
    DetectionEngine's role in Phase 4 — the only class the rest of the
    system needs to know about.
    """

    def __init__(
        self,
        *,
        evidence_collector: EvidenceCollector,
        classifier: AttackClassifier,
        confidence_engine: ConfidenceEngine,
        unknown_score_floor: float = _UNKNOWN_SCORE_FLOOR,
    ) -> None:
        self.evidence_collector = evidence_collector
        self.classifier = classifier
        self.confidence_engine = confidence_engine
        self.unknown_score_floor = unknown_score_floor

    def classify(self, evidence: EvidenceBundle, *, timestamp: datetime) -> ClassificationResult:
        scores = self.classifier.classify(evidence)
        chosen = self._select(scores, evidence)
        confidence = self.confidence_engine.compute_confidence(scores=scores, chosen=chosen, evidence=evidence)
        definition = get_attack_definition(chosen)
        mapping = map_attack(chosen)

        return ClassificationResult(
            event_id=evidence.event_id,
            entity_id=evidence.entity_id,
            timestamp=timestamp,
            entity_type=evidence.entity_type,
            attack_type=chosen,
            display_name=definition.display_name,
            confidence=confidence,
            severity=definition.typical_severity,
            mitre_tactic=mapping.tactic,
            mitre_technique=mapping.technique,
            evidence=scores.matched_indicators.get(chosen, ()),
            all_scores={attack_type.value: score for attack_type, score in scores.scores.items()},
            classification_strategy=self.classifier.strategy.name,
            detection_anomaly_score=evidence.anomaly_score,
            detection_risk_score=evidence.risk_score,
            detection_severity=evidence.severity,
            detection_verdict=evidence.verdict,
        )

    def _select(self, scores: ClassificationScores, evidence: EvidenceBundle) -> AttackType:
        top_score = max(scores.scores.values())
        if top_score < self.unknown_score_floor:
            return AttackType.UNKNOWN

        candidates = [attack_type for attack_type, score in scores.scores.items() if score == top_score]
        if len(candidates) == 1:
            return candidates[0]

        # Tie-break using each tied candidate's own primary Phase 4
        # deviation dimension, rather than an arbitrary (e.g. alphabetical)
        # order — the candidate whose most-associated dimension deviated
        # more strongly on THIS event is the more evidenced choice.
        def _tie_key(attack_type: AttackType) -> tuple[float, str]:
            dimension = PRIMARY_DIMENSION[attack_type]
            return (evidence.dimension_deviations.get(dimension, 0.0), attack_type.value)

        return max(candidates, key=_tie_key)


@dataclass(frozen=True)
class ClassificationEngineConfig:
    detection_results_path: Path
    engineered_events_path: Path
    profile_store_dir: Path
    output_dir: Path = field(default_factory=lambda: Path("data/classifications"))
    classification_strategy: str = "rule_based"
    confidence_config: ConfidenceEngineConfig = field(default_factory=ConfidenceEngineConfig)
    unknown_score_floor: float = _UNKNOWN_SCORE_FLOOR


def build_classification_engine(config: ClassificationEngineConfig) -> ClassificationEngine:
    return ClassificationEngine(
        evidence_collector=EvidenceCollector(),
        classifier=AttackClassifier(build_classification_strategy(config.classification_strategy)),
        confidence_engine=ConfidenceEngine(config.confidence_config),
        unknown_score_floor=config.unknown_score_floor,
    )


def _load_detection_results(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, low_memory=False)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
    return df[list(_DETECTION_COLUMNS)]


def _load_events(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, low_memory=False)
    columns = list(_FEATURE_COLUMNS)
    if "attack_type" in df.columns:
        columns.append("attack_type")
    return df[columns]


def run_classification(config: ClassificationEngineConfig) -> list[ClassificationResult]:
    """Classifies every event Phase 4 flagged as suspicious or anomalous.
    Normal-verdict events are walked over (to keep per-entity `previous
    resource` state causally correct across the *entire* stream, not just
    the flagged subset) but never classified — this phase performs
    classification only, never detection.

    Ground truth (`attack_type`), when present in the engineered events
    file, is attached to each result only AFTER classify() returns, via
    dataclasses.replace — identical discipline to Phase 4's is_attack
    handling, and never read by EvidenceCollector or AttackClassifier.
    """
    detection_df = _load_detection_results(config.detection_results_path)
    events_df = _load_events(config.engineered_events_path)
    merged = detection_df.merge(events_df, on="event_id", how="left")
    merged_sorted = merged.sort_values(["entity_id", "timestamp"], kind="stable").reset_index(drop=True)

    profile_store = ProfileStorage(config.profile_store_dir)
    engine = build_classification_engine(config)

    profile_cache: dict[str, BehaviourProfile | None] = {}
    history_cache: dict[str, list[BehaviourProfile]] = {}
    last_resource_by_entity: dict[str, str] = {}

    results: list[ClassificationResult] = []
    for row in merged_sorted.itertuples(index=False):
        entity_id = str(row.entity_id)
        if entity_id not in profile_cache:
            profile_cache[entity_id] = profile_store.load_latest(entity_id)
            history_cache[entity_id] = profile_store.load_history(entity_id)

        if row.verdict != "normal":
            previous_resource = last_resource_by_entity.get(entity_id)
            evidence = engine.evidence_collector.collect(
                row,
                profile=profile_cache[entity_id],
                profile_history=history_cache[entity_id],
                previous_resource=previous_resource,
            )
            result = engine.classify(evidence, timestamp=row.timestamp.to_pydatetime())
            ground_truth = getattr(row, "attack_type", None)
            if ground_truth is not None and pd.notna(ground_truth):
                result = replace(result, ground_truth_attack_type=str(ground_truth))
            results.append(result)

        last_resource_by_entity[entity_id] = str(row.resource_accessed)

    return results


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run SentinelAI attack classification over Phase 4 detection results.")
    parser.add_argument("--detection-results", type=Path, required=True, help="Path to detection_results.csv/.parquet (a Phase 4 run).")
    parser.add_argument("--events", type=Path, required=True, help="Path to engineered_events.csv/.parquet (a Phase 2C run).")
    parser.add_argument("--profile-store", type=Path, required=True, help="Path to the Phase 3 profile store directory.")
    parser.add_argument("--output-dir", type=Path, default=Path("data/classifications"))
    parser.add_argument("--classification-strategy", type=str, default="rule_based", choices=["rule_based"])
    return parser


def main() -> None:
    from classification.classification_validator import run_all_classification_validations
    from outputs.classification_writers import (
        write_attack_summary,
        write_classification_report,
        write_classification_validation_report,
        write_confidence_distribution,
    )

    args = build_arg_parser().parse_args()
    config = ClassificationEngineConfig(
        detection_results_path=args.detection_results,
        engineered_events_path=args.events,
        profile_store_dir=args.profile_store,
        output_dir=args.output_dir,
        classification_strategy=args.classification_strategy,
    )

    print(f"Loading detection results from: {config.detection_results_path}")
    print(f"Loading engineered events from: {config.engineered_events_path}")
    print(f"Loading profile store from: {config.profile_store_dir}")
    results = run_classification(config)
    print(f"Classified {len(results):,} flagged events using the '{config.classification_strategy}' strategy.")

    attack_type_counts = Counter(result.attack_type for result in results)
    for attack_type in AttackType:
        count = attack_type_counts.get(attack_type, 0)
        if count:
            print(f"  {attack_type.value}: {count:,}")

    validation_report = run_all_classification_validations(results)

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = config.output_dir / run_id

    write_classification_report(results, run_dir / "classification_report.csv", run_dir / "classification_report.parquet")
    write_attack_summary(results, run_dir / "attack_summary.md")
    write_confidence_distribution(results, run_dir / "confidence_distribution.md")
    write_classification_validation_report(validation_report, run_dir / "classification_validation_report.md")

    print(
        f"Validation: {'PASSED' if validation_report.passed else 'FAILED'} "
        f"({validation_report.error_count} errors, {validation_report.warning_count} warnings)"
    )
    print(f"Output written to: {run_dir.resolve()}")

    if not validation_report.passed:
        raise RuntimeError(
            f"Classification validation failed with {validation_report.error_count} error(s). "
            f"See {run_dir / 'classification_validation_report.md'} for details."
        )


if __name__ == "__main__":
    main()