from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from explainability.analyst_summary import AnalystSummary, AnalystSummaryBuilder
from explainability.confidence_explainer import ConfidenceExplainer, ConfidenceExplanation
from explainability.evidence_aggregator import EvidenceAggregator, ExplainabilityEvidence
from explainability.feature_attribution import FeatureAttributionEngine, FeatureContribution
from explainability.reason_generator import NarrativeExplanation, ReasonGenerator
from explainability.recommendation_engine import RecommendationEngine, RecommendedAction
from profiles.profile_manager import BehaviourProfile
from profiles.profile_storage import ProfileStorage

# Columns pulled from Phase 5's classification_report — the full row, since
# every column on it is already a decided, explainable fact.
_CLASSIFICATION_COLUMNS: tuple[str, ...] = (
    "event_id",
    "entity_id",
    "entity_type",
    "timestamp",
    "attack_type",
    "display_name",
    "confidence",
    "severity",
    "mitre_tactic",
    "mitre_technique",
    "evidence",
    "detection_anomaly_score",
    "detection_risk_score",
    "detection_severity",
    "detection_verdict",
    "score_brute_force",
    "score_impossible_travel",
    "score_credential_stuffing",
    "score_lateral_movement",
    "score_device_spoofing",
    "score_low_and_slow_exfiltration",
    "score_insider_drift",
)

# Columns pulled from Phase 4's detection_results — only the ones not
# already carried onto classification_report, to avoid duplicate columns
# on the merge.
_DETECTION_COLUMNS: tuple[str, ...] = (
    "event_id",
    "deviation_temporal",
    "deviation_device",
    "deviation_resource",
    "deviation_geographic",
    "deviation_authentication",
    "deviation_session",
    "risk_deviation_component",
    "risk_indicator_component",
    "risk_confidence_component",
    "risk_trust_component",
    "risk_cold_start_component",
    "historical_confidence",
    "entity_trust",
)

# Columns pulled from Phase 2C's engineered_events — the raw feature values
# every explanation is ultimately grounded in.
_FEATURE_COLUMNS: tuple[str, ...] = (
    "event_id",
    "login_result",
    "login_hour",
    "working_hours_deviation",
    "session_duration",
    "resource_accessed",
    "device_fingerprint",
    "geo_location",
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
    "behaviour_drift_score",
    "historical_percentile_session_duration",
    "history_length",
    "new_entity_flag",
)


@dataclass(frozen=True)
class ExplainabilityResult:
    """The complete Phase 6 output for one event: the evidence it was
    built from, and every derived explanation artifact."""

    event_id: str
    entity_id: str
    evidence: ExplainabilityEvidence
    contributions: tuple[FeatureContribution, ...]
    narrative: NarrativeExplanation
    confidence_explanation: ConfidenceExplanation
    recommendations: tuple[RecommendedAction, ...]
    summary: AnalystSummary

    def to_dict(self) -> dict[str, object]:
        row: dict[str, object] = {
            "event_id": self.event_id,
            "entity_id": self.entity_id,
            "risk_score": self.evidence.detection.risk_score,
            "attack_type": self.evidence.classification.attack_type,
            "confidence": self.evidence.classification.confidence,
            "confidence_level": self.confidence_explanation.level.value,
            "severity": self.evidence.detection.severity,
        }
        for index, contribution in enumerate(self.contributions, start=1):
            row[f"top{index}_dimension"] = contribution.dimension
            row[f"top{index}_contribution_pct"] = contribution.contribution_percentage
            row[f"top{index}_explanation"] = contribution.explanation
        row.update(self.narrative.to_dict())
        row.update(self.confidence_explanation.to_dict())
        row["recommended_actions"] = " | ".join(f"[{a.priority}] {a.action}" for a in self.recommendations)
        return row


class ExplainabilityEngine:
    """Coordinates the complete explainability workflow for one already
    classified event: aggregate evidence, attribute features, generate a
    narrative, explain the confidence, recommend actions, and assemble the
    analyst summary. Mirrors DetectionEngine/ClassificationEngine's role
    in Phases 4/5 — the only class the rest of the system needs to know
    about.
    """

    def __init__(
        self,
        *,
        evidence_aggregator: EvidenceAggregator,
        feature_attribution: FeatureAttributionEngine,
        reason_generator: ReasonGenerator,
        confidence_explainer: ConfidenceExplainer,
        recommendation_engine: RecommendationEngine,
        summary_builder: AnalystSummaryBuilder,
    ) -> None:
        self.evidence_aggregator = evidence_aggregator
        self.feature_attribution = feature_attribution
        self.reason_generator = reason_generator
        self.confidence_explainer = confidence_explainer
        self.recommendation_engine = recommendation_engine
        self.summary_builder = summary_builder

    def explain(
        self,
        row: object,
        *,
        profile: BehaviourProfile | None,
        profile_history: list[BehaviourProfile],
    ) -> ExplainabilityResult:
        evidence = self.evidence_aggregator.aggregate(row, profile=profile, profile_history=profile_history)
        contributions = self.feature_attribution.attribute(evidence)
        narrative = self.reason_generator.generate(evidence, contributions)
        confidence_explanation = self.confidence_explainer.explain(evidence)
        recommendations = self.recommendation_engine.recommend(evidence)
        summary = self.summary_builder.build(
            evidence=evidence,
            contributions=contributions,
            narrative=narrative,
            confidence_explanation=confidence_explanation,
            recommendations=recommendations,
        )

        return ExplainabilityResult(
            event_id=evidence.event_id,
            entity_id=evidence.entity_id,
            evidence=evidence,
            contributions=contributions,
            narrative=narrative,
            confidence_explanation=confidence_explanation,
            recommendations=recommendations,
            summary=summary,
        )


def build_explainability_engine() -> ExplainabilityEngine:
    return ExplainabilityEngine(
        evidence_aggregator=EvidenceAggregator(),
        feature_attribution=FeatureAttributionEngine(),
        reason_generator=ReasonGenerator(),
        confidence_explainer=ConfidenceExplainer(),
        recommendation_engine=RecommendationEngine(),
        summary_builder=AnalystSummaryBuilder(),
    )


@dataclass(frozen=True)
class ExplainabilityEngineConfig:
    classification_results_path: Path
    detection_results_path: Path
    engineered_events_path: Path
    profile_store_dir: Path
    output_dir: Path = Path("data/explainability")


def _load_classification_results(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, low_memory=False)
    return df[list(_CLASSIFICATION_COLUMNS)]


def _load_detection_results(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, low_memory=False)
    return df[list(_DETECTION_COLUMNS)]


def _load_events(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, low_memory=False)
    return df[list(_FEATURE_COLUMNS)]


def run_explainability(config: ExplainabilityEngineConfig) -> list[ExplainabilityResult]:
    """Explains every event Phase 5 classified. No filtering happens here
    — Phase 5's classification_report already contains only the events
    Phase 4 flagged Suspicious or Anomalous, and this phase performs
    explainability only, never detection or classification.
    """
    classification_df = _load_classification_results(config.classification_results_path)
    detection_df = _load_detection_results(config.detection_results_path)
    features_df = _load_events(config.engineered_events_path)

    merged = classification_df.merge(detection_df, on="event_id", how="left").merge(
        features_df, on="event_id", how="left"
    )

    profile_store = ProfileStorage(config.profile_store_dir)
    engine = build_explainability_engine()

    profile_cache: dict[str, BehaviourProfile | None] = {}
    history_cache: dict[str, list[BehaviourProfile]] = {}

    results: list[ExplainabilityResult] = []
    for row in merged.itertuples(index=False):
        entity_id = str(row.entity_id)
        if entity_id not in profile_cache:
            profile_cache[entity_id] = profile_store.load_latest(entity_id)
            history_cache[entity_id] = profile_store.load_history(entity_id)

        result = engine.explain(row, profile=profile_cache[entity_id], profile_history=history_cache[entity_id])
        results.append(result)

    return results


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run SentinelAI explainability over Phase 5 classification results.")
    parser.add_argument("--classification-results", type=Path, required=True, help="Path to classification_report.csv/.parquet (a Phase 5 run).")
    parser.add_argument("--detection-results", type=Path, required=True, help="Path to detection_results.csv/.parquet (a Phase 4 run).")
    parser.add_argument("--events", type=Path, required=True, help="Path to engineered_events.csv/.parquet (a Phase 2C run).")
    parser.add_argument("--profile-store", type=Path, required=True, help="Path to the Phase 3 profile store directory.")
    parser.add_argument("--output-dir", type=Path, default=Path("data/explainability"))
    return parser


def main() -> None:
    from datetime import datetime

    from explainability.explainability_validator import run_all_explainability_validations
    from outputs.explainability_writers import (
        write_analyst_summary,
        write_explainability_report,
        write_feature_attribution_report,
        write_recommendation_report,
        write_explainability_validation_report,
    )

    args = build_arg_parser().parse_args()
    config = ExplainabilityEngineConfig(
        classification_results_path=args.classification_results,
        detection_results_path=args.detection_results,
        engineered_events_path=args.events,
        profile_store_dir=args.profile_store,
        output_dir=args.output_dir,
    )

    print(f"Loading classification results from: {config.classification_results_path}")
    print(f"Loading detection results from: {config.detection_results_path}")
    print(f"Loading engineered events from: {config.engineered_events_path}")
    print(f"Loading profile store from: {config.profile_store_dir}")
    results = run_explainability(config)
    print(f"Generated explanations for {len(results):,} classified events.")

    validation_report = run_all_explainability_validations(results)

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = config.output_dir / run_id

    write_explainability_report(results, run_dir / "explainability_report.csv", run_dir / "explainability_report.parquet")
    write_feature_attribution_report(results, run_dir / "feature_attribution_report.md")
    write_recommendation_report(results, run_dir / "recommendation_report.md")
    write_analyst_summary(results, run_dir / "analyst_summary.csv", run_dir / "analyst_summary.parquet", run_dir / "analyst_summary.md")
    write_explainability_validation_report(validation_report, run_dir / "explainability_validation_report.md")

    print(
        f"Validation: {'PASSED' if validation_report.passed else 'FAILED'} "
        f"({validation_report.error_count} errors, {validation_report.warning_count} warnings)"
    )
    print(f"Output written to: {run_dir.resolve()}")

    if not validation_report.passed:
        raise RuntimeError(
            f"Explainability validation failed with {validation_report.error_count} error(s). "
            f"See {run_dir / 'explainability_validation_report.md'} for details."
        )


if __name__ == "__main__":
    main()