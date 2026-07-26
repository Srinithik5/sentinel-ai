from __future__ import annotations

from dataclasses import dataclass

from classification.attack_registry import KNOWN_ATTACK_TYPES
from profiles.profile_manager import BehaviourProfile

_DIMENSION_NAMES: tuple[str, ...] = ("temporal", "device", "resource", "geographic", "authentication", "session")


@dataclass(frozen=True)
class DetectionEvidence:
    """Everything Phase 4 already decided about this event, read back from
    `detection_results.csv` — never recomputed. Explainability narrates an
    existing decision, it does not reach a new one.
    """

    anomaly_score: float
    risk_score: float
    severity: str
    verdict: str
    dimension_deviations: dict[str, float]
    risk_deviation_component: float
    risk_indicator_component: float
    risk_confidence_component: float
    risk_trust_component: float
    risk_cold_start_component: float
    historical_confidence: float
    entity_trust: float


@dataclass(frozen=True)
class ClassificationEvidence:
    """Everything Phase 5 already decided about this event, read back from
    `classification_report.csv` — never recomputed.
    """

    attack_type: str
    display_name: str
    confidence: float
    severity: str
    mitre_tactic: str
    mitre_technique: str
    matched_indicators: tuple[str, ...]
    attack_type_scores: dict[str, float]


@dataclass(frozen=True)
class FeatureEvidence:
    """The Phase 2C engineered feature values for this event — read
    directly, never re-derived, so explanations always describe the exact
    numbers detection and classification actually saw.
    """

    login_result: str
    login_hour: int
    working_hours_deviation: float
    session_duration: float
    resource_accessed: str
    device_fingerprint: str
    geo_location: str
    consecutive_failures: int
    burst_access_score: float
    mfa_usage_frequency: float
    geo_velocity_kmh: float
    country_change: bool
    geo_novelty: bool
    device_familiarity_score: float
    fingerprint_mismatch: bool
    os_novelty: bool
    mac_novelty: bool
    resource_novelty: bool
    resource_diversity: float
    sensitive_resource_access: bool
    privilege_change_indicator: bool
    session_entropy: float
    behaviour_drift_score: float
    historical_percentile_session_duration: float
    history_length: int
    new_entity_flag: bool


@dataclass(frozen=True)
class ProfileEvidence:
    """A snapshot of the entity's current Phase 3 behaviour baseline —
    the "what does normal look like for this entity" half of every
    historical comparison.
    """

    has_profile: bool
    profile_version: int | None
    avg_login_hour: float | None
    login_hour_std: float | None
    avg_session_duration: float | None
    session_duration_std: float | None
    failure_rate: float | None
    device_frequency: float | None
    resource_frequency: float | None
    geo_frequency: float | None
    resource_sharing_score: float | None
    drift_score: float | None
    drifted_dimensions: tuple[str, ...]
    warmup_strategy: str | None


@dataclass(frozen=True)
class HistoricalContext:
    """How the entity's own baseline has evolved across every stored
    profile version — distinct from ProfileEvidence, which is only the
    *current* snapshot.
    """

    profile_version_count: int
    drift_score_trend: tuple[float, ...]
    sample_count_trend: tuple[int, ...]


@dataclass(frozen=True)
class ExplainabilityEvidence:
    """The complete, typed evidence bundle for one event, gathered from
    all five required sources: Detection, Classification, Feature
    Engineering, Behaviour Profiles, and Historical Context.
    """

    event_id: str
    entity_id: str
    entity_type: str | None
    timestamp: str
    detection: DetectionEvidence
    classification: ClassificationEvidence
    features: FeatureEvidence
    profile: ProfileEvidence
    history: HistoricalContext


class EvidenceAggregator:
    """Assembles an ExplainabilityEvidence bundle for one event from a
    merged detection+classification+feature row and the entity's Phase 3
    profile. Every method is a pure read of already-computed upstream
    state — no I/O, no recomputation of any Phase 4/5 decision.
    """

    def aggregate(
        self,
        row: object,
        *,
        profile: BehaviourProfile | None,
        profile_history: list[BehaviourProfile],
    ) -> ExplainabilityEvidence:
        detection = self._detection_evidence(row)
        classification = self._classification_evidence(row)
        features = self._feature_evidence(row)
        profile_evidence = self._profile_evidence(row, profile)
        history = self._historical_context(profile_history)

        return ExplainabilityEvidence(
            event_id=str(row.event_id),
            entity_id=str(row.entity_id),
            entity_type=str(row.entity_type) if getattr(row, "entity_type", None) else None,
            timestamp=str(row.timestamp),
            detection=detection,
            classification=classification,
            features=features,
            profile=profile_evidence,
            history=history,
        )

    def _detection_evidence(self, row: object) -> DetectionEvidence:
        dimension_deviations = {
            dimension: float(getattr(row, f"deviation_{dimension}", 0.0)) for dimension in _DIMENSION_NAMES
        }
        return DetectionEvidence(
            anomaly_score=float(row.detection_anomaly_score),
            risk_score=float(row.detection_risk_score),
            severity=str(row.detection_severity),
            verdict=str(row.detection_verdict),
            dimension_deviations=dimension_deviations,
            risk_deviation_component=float(row.risk_deviation_component),
            risk_indicator_component=float(row.risk_indicator_component),
            risk_confidence_component=float(row.risk_confidence_component),
            risk_trust_component=float(row.risk_trust_component),
            risk_cold_start_component=float(row.risk_cold_start_component),
            historical_confidence=float(row.historical_confidence),
            entity_trust=float(row.entity_trust),
        )

    def _classification_evidence(self, row: object) -> ClassificationEvidence:
        evidence_text = str(getattr(row, "evidence", "") or "")
        matched_indicators = tuple(part for part in evidence_text.split(" | ") if part)
        attack_type_scores = {
            attack_type.value: float(getattr(row, f"score_{attack_type.value}", 0.0))
            for attack_type in KNOWN_ATTACK_TYPES
        }
        return ClassificationEvidence(
            attack_type=str(row.attack_type),
            display_name=str(row.display_name),
            confidence=float(row.confidence),
            severity=str(row.severity),
            mitre_tactic=str(row.mitre_tactic),
            mitre_technique=str(row.mitre_technique),
            matched_indicators=matched_indicators,
            attack_type_scores=attack_type_scores,
        )

    def _feature_evidence(self, row: object) -> FeatureEvidence:
        return FeatureEvidence(
            login_result=str(row.login_result),
            login_hour=int(row.login_hour),
            working_hours_deviation=float(row.working_hours_deviation),
            session_duration=float(row.session_duration),
            resource_accessed=str(row.resource_accessed),
            device_fingerprint=str(row.device_fingerprint),
            geo_location=str(row.geo_location),
            consecutive_failures=int(row.consecutive_failures),
            burst_access_score=float(row.burst_access_score),
            mfa_usage_frequency=float(row.mfa_usage_frequency),
            geo_velocity_kmh=float(row.geo_velocity_kmh),
            country_change=bool(row.country_change),
            geo_novelty=bool(row.geo_novelty),
            device_familiarity_score=float(row.device_familiarity_score),
            fingerprint_mismatch=bool(row.fingerprint_mismatch),
            os_novelty=bool(row.os_novelty),
            mac_novelty=bool(row.mac_novelty),
            resource_novelty=bool(row.resource_novelty),
            resource_diversity=float(row.resource_diversity),
            sensitive_resource_access=bool(row.sensitive_resource_access),
            privilege_change_indicator=bool(row.privilege_change_indicator),
            session_entropy=float(row.session_entropy),
            behaviour_drift_score=float(row.behaviour_drift_score),
            historical_percentile_session_duration=float(row.historical_percentile_session_duration),
            history_length=int(row.history_length),
            new_entity_flag=bool(row.new_entity_flag),
        )

    def _profile_evidence(self, row: object, profile: BehaviourProfile | None) -> ProfileEvidence:
        if profile is None:
            return ProfileEvidence(
                has_profile=False,
                profile_version=None,
                avg_login_hour=None,
                login_hour_std=None,
                avg_session_duration=None,
                session_duration_std=None,
                failure_rate=None,
                device_frequency=None,
                resource_frequency=None,
                geo_frequency=None,
                resource_sharing_score=None,
                drift_score=None,
                drifted_dimensions=(),
                warmup_strategy=None,
            )

        stats = profile.statistical
        return ProfileEvidence(
            has_profile=True,
            profile_version=profile.version,
            avg_login_hour=stats.avg_login_hour,
            login_hour_std=stats.login_hour_std,
            avg_session_duration=stats.avg_session_duration,
            session_duration_std=stats.session_duration_std,
            failure_rate=stats.failure_rate,
            device_frequency=stats.device_frequency.get(str(row.device_fingerprint), 0.0),
            resource_frequency=stats.resource_frequency.get(str(row.resource_accessed), 0.0),
            geo_frequency=stats.geo_frequency.get(str(row.geo_location), 0.0),
            resource_sharing_score=profile.relationship.resource_sharing_score,
            drift_score=profile.drift.drift_score,
            drifted_dimensions=profile.drift.drifted_dimensions,
            warmup_strategy=profile.cold_start.warmup_strategy.value,
        )

    def _historical_context(self, profile_history: list[BehaviourProfile]) -> HistoricalContext:
        return HistoricalContext(
            profile_version_count=len(profile_history),
            drift_score_trend=tuple(version.drift.drift_score for version in profile_history),
            sample_count_trend=tuple(version.statistical.sample_count for version in profile_history),
        )