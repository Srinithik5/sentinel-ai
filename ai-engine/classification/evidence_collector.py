from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from profiles.profile_manager import BehaviourProfile

_DIMENSION_NAMES: tuple[str, ...] = ("temporal", "device", "resource", "geographic", "authentication", "session")


@dataclass(frozen=True)
class EvidenceBundle:
    """Everything AttackClassifier needs about one already-flagged event,
    gathered from four sources: Phase 4's own detection scores, Phase 2C's
    engineered features, Phase 3's behaviour profile, and the entity's
    historical profile-version trend. Deliberately excludes every Phase 2B
    ground-truth column (attack_type, mitre_tactic, mitre_technique,
    attack_id, confidence, description, injected, is_attack) — those are
    attached to the final ClassificationResult only AFTER classification,
    for evaluation, mirroring Phase 4's is_attack discipline exactly.
    """

    event_id: str
    entity_id: str
    entity_type: str | None

    # Phase 4 detection scores
    anomaly_score: float
    risk_score: float
    severity: str
    verdict: str
    dimension_deviations: dict[str, float]

    # Phase 2C engineered features (causal, per-event — never ground truth)
    login_result: str
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
    command_sequence_complexity: float
    behaviour_drift_score: float
    historical_percentile_session_duration: float
    history_length: int
    new_entity_flag: bool

    # Phase 3 behaviour profile
    resource_sharing_score: float | None
    profile_drift_score: float | None
    drifted_dimensions: tuple[str, ...]
    warmup_strategy: str | None
    resource_transition_probability: float | None

    # Historical activity — the entity's own profile-version trend
    profile_version_count: int
    drift_score_trend: tuple[float, ...]

    def to_dict(self) -> dict[str, object]:
        row: dict[str, object] = {
            "event_id": self.event_id,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "anomaly_score": self.anomaly_score,
            "risk_score": self.risk_score,
            "severity": self.severity,
            "verdict": self.verdict,
        }
        for dimension, score in self.dimension_deviations.items():
            row[f"deviation_{dimension}"] = score
        return row


class EvidenceCollector:
    """Assembles an EvidenceBundle for one event. Every method here is a
    pure read of already-computed upstream state (a merged detection +
    feature row, a Phase 3 BehaviourProfile, and its version history) — no
    recomputation of anything Phase 2C or Phase 3 already produced, and no
    I/O of its own (callers pass in whatever ProfileStorage already loaded).
    """

    def collect(
        self,
        row: object,
        *,
        profile: BehaviourProfile | None,
        profile_history: list[BehaviourProfile],
        previous_resource: str | None,
    ) -> EvidenceBundle:
        dimension_deviations = {
            dimension: float(getattr(row, f"deviation_{dimension}", 0.0)) for dimension in _DIMENSION_NAMES
        }

        resource_sharing_score = profile.relationship.resource_sharing_score if profile is not None else None
        profile_drift_score = profile.drift.drift_score if profile is not None else None
        drifted_dimensions = profile.drift.drifted_dimensions if profile is not None else ()
        warmup_strategy = profile.cold_start.warmup_strategy.value if profile is not None else None

        resource_transition_probability: float | None = None
        if profile is not None and previous_resource is not None:
            transitions = profile.sequence.resource_transition_matrix.get(previous_resource, {})
            resource_transition_probability = transitions.get(str(row.resource_accessed), 0.0)

        drift_score_trend = tuple(version.drift.drift_score for version in profile_history)

        entity_type = getattr(row, "entity_type", None)

        return EvidenceBundle(
            event_id=str(row.event_id),
            entity_id=str(row.entity_id),
            entity_type=str(entity_type) if pd.notna(entity_type) else None,
            anomaly_score=float(row.anomaly_score),
            risk_score=float(row.risk_score),
            severity=str(row.severity),
            verdict=str(row.verdict),
            dimension_deviations=dimension_deviations,
            login_result=str(row.login_result),
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
            command_sequence_complexity=float(row.command_sequence_complexity),
            behaviour_drift_score=float(row.behaviour_drift_score),
            historical_percentile_session_duration=float(row.historical_percentile_session_duration),
            history_length=int(row.history_length),
            new_entity_flag=bool(row.new_entity_flag),
            resource_sharing_score=resource_sharing_score,
            profile_drift_score=profile_drift_score,
            drifted_dimensions=drifted_dimensions,
            warmup_strategy=warmup_strategy,
            resource_transition_probability=resource_transition_probability,
            profile_version_count=len(profile_history),
            drift_score_trend=drift_score_trend,
        )