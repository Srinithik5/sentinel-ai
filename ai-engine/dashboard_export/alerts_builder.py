from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from profiles.profile_manager import BehaviourProfile
from profiles.profile_storage import ProfileStorage

_DEFAULT_SAMPLE_PER_ATTACK_TYPE = 45
_DEFAULT_HISTORY_WINDOW = 12
_FEATURE_CONTRIBUTION_SLOTS = 6
_EM_DASH = "—"


@dataclass(frozen=True)
class DimensionDeviations:
    temporal: float
    device: float
    resource: float
    geographic: float
    authentication: float
    session: float

    def to_dict(self) -> dict[str, float]:
        return {
            "temporal": self.temporal,
            "device": self.device,
            "resource": self.resource,
            "geographic": self.geographic,
            "authentication": self.authentication,
            "session": self.session,
        }


@dataclass(frozen=True)
class RecommendedAction:
    priority: str
    action: str
    rationale: str

    def to_dict(self) -> dict[str, str]:
        return {"priority": self.priority, "action": self.action, "rationale": self.rationale}


@dataclass(frozen=True)
class FeatureContribution:
    dimension: str
    contribution_percentage: float
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return {
            "dimension": self.dimension,
            "contributionPercentage": self.contribution_percentage,
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class HistoryEvent:
    timestamp: str
    resource_accessed: str
    device_fingerprint: str
    geo_location: str
    login_result: str
    session_duration: float
    auth_method: str

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "resourceAccessed": self.resource_accessed,
            "deviceFingerprint": self.device_fingerprint,
            "geoLocation": self.geo_location,
            "loginResult": self.login_result,
            "sessionDuration": self.session_duration,
            "authMethod": self.auth_method,
        }


@dataclass(frozen=True)
class AlertFeatureSnapshot:
    login_result: str
    login_hour: int
    session_duration: float
    resource_accessed: str
    device_fingerprint: str
    geo_location: str
    consecutive_failures: int
    geo_velocity_kmh: float
    auth_method: str
    sensitive_resource_access: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "loginResult": self.login_result,
            "loginHour": self.login_hour,
            "sessionDuration": self.session_duration,
            "resourceAccessed": self.resource_accessed,
            "deviceFingerprint": self.device_fingerprint,
            "geoLocation": self.geo_location,
            "consecutiveFailures": self.consecutive_failures,
            "geoVelocityKmh": self.geo_velocity_kmh,
            "authMethod": self.auth_method,
            "sensitiveResourceAccess": self.sensitive_resource_access,
        }


@dataclass(frozen=True)
class ProfileBaseline:
    avg_session_duration: float
    session_duration_std: float
    avg_login_hour: float
    login_hour_std: float
    sample_count: int
    failure_rate: float
    profile_version: int
    drift_score: float
    warmup_strategy: str

    def to_dict(self) -> dict[str, object]:
        return {
            "avgSessionDuration": self.avg_session_duration,
            "sessionDurationStd": self.session_duration_std,
            "avgLoginHour": self.avg_login_hour,
            "loginHourStd": self.login_hour_std,
            "sampleCount": self.sample_count,
            "failureRate": self.failure_rate,
            "profileVersion": self.profile_version,
            "driftScore": self.drift_score,
            "warmupStrategy": self.warmup_strategy,
        }


@dataclass(frozen=True)
class Alert:
    event_id: str
    entity_id: str
    entity_type: str | None
    department: str | None
    role: str | None
    home_location: str | None
    timezone: str | None
    timestamp: str
    risk_score: float
    anomaly_score: float
    severity: str
    verdict: str
    attack_type: str
    attack_display_name: str
    confidence: float
    confidence_level: str
    mitre_tactic: str
    mitre_technique: str
    dimension_deviations: DimensionDeviations
    top_indicators: tuple[str, ...]
    feature_contributions: tuple[FeatureContribution, ...]
    evidence_summary: str
    confidence_explanation: str
    recommended_actions: tuple[RecommendedAction, ...]
    matched_indicators: tuple[str, ...]
    feature: AlertFeatureSnapshot
    history: tuple[HistoryEvent, ...]
    profile_baseline: ProfileBaseline | None

    def to_dict(self) -> dict[str, object]:
        return {
            "eventId": self.event_id,
            "entityId": self.entity_id,
            "entityType": self.entity_type,
            "department": self.department,
            "role": self.role,
            "homeLocation": self.home_location,
            "timezone": self.timezone,
            "timestamp": self.timestamp,
            "riskScore": self.risk_score,
            "anomalyScore": self.anomaly_score,
            "severity": self.severity,
            "verdict": self.verdict,
            "attackType": self.attack_type,
            "attackDisplayName": self.attack_display_name,
            "confidence": self.confidence,
            "confidenceLevel": self.confidence_level,
            "mitreTactic": self.mitre_tactic,
            "mitreTechnique": self.mitre_technique,
            "dimensionDeviations": self.dimension_deviations.to_dict(),
            "topIndicators": list(self.top_indicators),
            "featureContributions": [item.to_dict() for item in self.feature_contributions],
            "evidenceSummary": self.evidence_summary,
            "confidenceExplanation": self.confidence_explanation,
            "recommendedActions": [item.to_dict() for item in self.recommended_actions],
            "matchedIndicators": list(self.matched_indicators),
            "feature": self.feature.to_dict(),
            "history": [item.to_dict() for item in self.history],
            "profileBaseline": self.profile_baseline.to_dict() if self.profile_baseline else None,
        }


def _profile_baseline(profile_store: ProfileStorage, entity_id: str) -> ProfileBaseline | None:
    profile: BehaviourProfile | None = profile_store.load_latest(entity_id)
    if profile is None:
        return None
    stats = profile.statistical
    return ProfileBaseline(
        avg_session_duration=stats.avg_session_duration,
        session_duration_std=stats.session_duration_std,
        avg_login_hour=stats.avg_login_hour,
        login_hour_std=stats.login_hour_std,
        sample_count=stats.sample_count,
        failure_rate=stats.failure_rate,
        profile_version=profile.version,
        drift_score=profile.drift.drift_score,
        warmup_strategy=profile.cold_start.warmup_strategy.value,
    )


def _history_for_entity(events_df: pd.DataFrame, entity_id: str, before: pd.Timestamp, window: int) -> tuple[HistoryEvent, ...]:
    entity_events = events_df[(events_df["entity_id"] == entity_id) & (events_df["timestamp"] <= before)]
    entity_events = entity_events.sort_values("timestamp").tail(window)
    return tuple(
        HistoryEvent(
            timestamp=row.timestamp.isoformat(),
            resource_accessed=str(row.resource_accessed),
            device_fingerprint=str(row.device_fingerprint),
            geo_location=str(row.geo_location),
            login_result=str(row.login_result),
            session_duration=float(row.session_duration),
            auth_method=str(row.auth_method),
        )
        for row in entity_events.itertuples(index=False)
    )


def _parse_recommended_actions(raw: object) -> tuple[RecommendedAction, ...]:
    """Parses Phase 6's `"[priority] action — rationale"` pipe-delimited
    string (see explainability/recommendation_engine.py) into structured
    entries. Falls back to a bare "standard" action if an entry doesn't
    match the expected shape, rather than dropping it silently.
    """
    if pd.isna(raw) or not raw:
        return ()
    actions: list[RecommendedAction] = []
    for entry in str(raw).split(" | "):
        try:
            priority = entry.split("]")[0].strip("[")
            rest = entry.split("]", 1)[1].strip()
            if f" {_EM_DASH} " in rest:
                action, rationale = rest.split(f" {_EM_DASH} ", 1)
            else:
                action, rationale = rest, ""
        except (IndexError, ValueError):
            priority, action, rationale = "standard", entry, ""
        actions.append(RecommendedAction(priority=priority, action=action.strip(), rationale=rationale.strip()))
    return tuple(actions)


def _feature_contributions(row: object) -> tuple[FeatureContribution, ...]:
    contributions: list[FeatureContribution] = []
    for index in range(1, _FEATURE_CONTRIBUTION_SLOTS + 1):
        dimension = getattr(row, f"top{index}_dimension")
        if pd.isna(dimension):
            continue
        contributions.append(
            FeatureContribution(
                dimension=dimension,
                contribution_percentage=round(float(getattr(row, f"top{index}_contribution_pct")), 2),
                explanation=getattr(row, f"top{index}_explanation"),
            )
        )
    return tuple(contributions)


def build_alerts(
    *,
    classification_df: pd.DataFrame,
    detection_df: pd.DataFrame,
    analyst_summary_df: pd.DataFrame,
    explainability_report_df: pd.DataFrame,
    events_df: pd.DataFrame,
    entities_df: pd.DataFrame,
    profile_store: ProfileStorage,
    sample_per_attack_type: int = _DEFAULT_SAMPLE_PER_ATTACK_TYPE,
    history_window: int = _DEFAULT_HISTORY_WINDOW,
) -> tuple[Alert, ...]:
    """Builds the dashboard's alert feed: every classified event, capped
    at `sample_per_attack_type` per attack type (highest risk first), each
    enriched with real Phase 4 dimension deviations, Phase 6 evidence/
    recommendations/feature-attribution, raw Phase 2C feature values, a
    real recent-event history window, and the entity's real Phase 3
    profile baseline. Sampling is deterministic (sort + groupby head, no
    randomness) so the same inputs always produce the same alert set.
    """
    contribution_cols = [
        col
        for index in range(1, _FEATURE_CONTRIBUTION_SLOTS + 1)
        for col in (f"top{index}_dimension", f"top{index}_contribution_pct", f"top{index}_explanation")
    ]

    merged = (
        classification_df.merge(
            detection_df[
                [
                    "event_id",
                    "deviation_temporal",
                    "deviation_device",
                    "deviation_resource",
                    "deviation_geographic",
                    "deviation_authentication",
                    "deviation_session",
                ]
            ],
            on="event_id",
            how="left",
        )
        .merge(
            analyst_summary_df[
                ["event_id", "top_indicators", "evidence_summary", "recommended_actions", "confidence_level", "confidence_explanation"]
            ],
            on="event_id",
            how="left",
        )
        .merge(explainability_report_df[["event_id"] + contribution_cols], on="event_id", how="left")
        .merge(
            events_df[
                [
                    "event_id",
                    "login_result",
                    "login_hour",
                    "session_duration",
                    "resource_accessed",
                    "device_fingerprint",
                    "geo_location",
                    "consecutive_failures",
                    "geo_velocity_kmh",
                    "auth_method",
                    "sensitive_resource_access",
                ]
            ],
            on="event_id",
            how="left",
        )
    )

    entity_lookup = entities_df.set_index("entity_id")[["department", "role", "home_location", "timezone"]].to_dict("index")

    sampled = (
        merged.sort_values("detection_risk_score", ascending=False)
        .groupby("attack_type", group_keys=False)
        .head(sample_per_attack_type)
        .sort_values("detection_risk_score", ascending=False)
        .reset_index(drop=True)
    )

    alerts: list[Alert] = []
    for row in sampled.itertuples(index=False):
        entity_meta = entity_lookup.get(row.entity_id, {})
        matched_indicators = tuple(str(row.evidence).split(" | ")) if pd.notna(row.evidence) and row.evidence else ()
        top_indicators = tuple(str(row.top_indicators).split(" | ")) if pd.notna(row.top_indicators) else ()

        alerts.append(
            Alert(
                event_id=row.event_id,
                entity_id=row.entity_id,
                entity_type=row.entity_type if pd.notna(row.entity_type) else None,
                department=entity_meta.get("department"),
                role=entity_meta.get("role"),
                home_location=entity_meta.get("home_location"),
                timezone=entity_meta.get("timezone"),
                timestamp=row.timestamp.isoformat(),
                risk_score=round(float(row.detection_risk_score), 2),
                anomaly_score=round(float(row.detection_anomaly_score), 4),
                severity=row.detection_severity,
                verdict=row.detection_verdict,
                attack_type=row.attack_type,
                attack_display_name=row.display_name,
                confidence=round(float(row.confidence), 4),
                confidence_level=row.confidence_level if pd.notna(row.confidence_level) else "low",
                mitre_tactic=row.mitre_tactic,
                mitre_technique=row.mitre_technique,
                dimension_deviations=DimensionDeviations(
                    temporal=round(float(row.deviation_temporal), 4),
                    device=round(float(row.deviation_device), 4),
                    resource=round(float(row.deviation_resource), 4),
                    geographic=round(float(row.deviation_geographic), 4),
                    authentication=round(float(row.deviation_authentication), 4),
                    session=round(float(row.deviation_session), 4),
                ),
                top_indicators=top_indicators,
                feature_contributions=_feature_contributions(row),
                evidence_summary=row.evidence_summary if pd.notna(row.evidence_summary) else "",
                confidence_explanation=row.confidence_explanation if pd.notna(row.confidence_explanation) else "",
                recommended_actions=_parse_recommended_actions(row.recommended_actions),
                matched_indicators=matched_indicators,
                feature=AlertFeatureSnapshot(
                    login_result=row.login_result,
                    login_hour=int(row.login_hour),
                    session_duration=float(row.session_duration),
                    resource_accessed=row.resource_accessed,
                    device_fingerprint=row.device_fingerprint,
                    geo_location=row.geo_location,
                    consecutive_failures=int(row.consecutive_failures),
                    geo_velocity_kmh=float(row.geo_velocity_kmh),
                    auth_method=row.auth_method,
                    sensitive_resource_access=bool(row.sensitive_resource_access),
                ),
                history=_history_for_entity(events_df, row.entity_id, row.timestamp, history_window),
                profile_baseline=_profile_baseline(profile_store, row.entity_id),
            )
        )

    return tuple(alerts)