from __future__ import annotations

from dataclasses import dataclass

from classification.attack_registry import ATTACK_REGISTRY
from dashboard_export.alerts_builder import Alert
from dashboard_export.analytics_builder import AnalyticsData
from dashboard_export.mitre_builder import MitreEntry
from dashboard_export.overview_builder import OverviewMetrics
from dashboard_export.system_health_builder import SystemHealthData

_KNOWN_SEVERITIES = {"informational", "low", "medium", "high", "critical"}
_KNOWN_VERDICTS = {"normal", "suspicious", "anomalous"}
_KNOWN_CONFIDENCE_LEVELS = {"low", "medium", "high"}
_HOURS_IN_DAY = 24


@dataclass(frozen=True)
class ValidationIssue:
    check: str
    severity: str  # "error" | "warning"
    message: str


@dataclass(frozen=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...]

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")


def validate_overview(overview: OverviewMetrics) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if overview.total_events <= 0:
        issues.append(ValidationIssue("overview_total_events", "error", "totalEvents must be positive."))
    if overview.anomalies > overview.total_events:
        issues.append(ValidationIssue("overview_anomaly_bound", "error", "anomalies exceeds totalEvents."))
    if overview.critical_alerts > overview.anomalies:
        issues.append(ValidationIssue("overview_critical_bound", "error", "criticalAlerts exceeds anomalies."))
    if not 0.0 <= overview.detection_accuracy <= 100.0:
        issues.append(ValidationIssue("overview_accuracy_range", "error", f"detectionAccuracy={overview.detection_accuracy} outside [0,100]."))
    if not 0.0 <= overview.false_positive_rate <= 100.0:
        issues.append(ValidationIssue("overview_fpr_range", "error", f"falsePositiveRate={overview.false_positive_rate} outside [0,100]."))
    if overview.detection_latency_ms < 0:
        issues.append(ValidationIssue("overview_latency_range", "error", "detectionLatencyMs is negative."))
    return issues


def validate_alerts(alerts: tuple[Alert, ...]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not alerts:
        issues.append(ValidationIssue("alerts_present", "error", "No alerts were exported."))
    for alert in alerts:
        if not 0.0 <= alert.risk_score <= 100.0:
            issues.append(ValidationIssue("alert_risk_score_range", "error", f"{alert.event_id}: riskScore={alert.risk_score} outside [0,100]."))
        if not 0.0 <= alert.confidence <= 1.0:
            issues.append(ValidationIssue("alert_confidence_range", "error", f"{alert.event_id}: confidence={alert.confidence} outside [0,1]."))
        if alert.severity not in _KNOWN_SEVERITIES:
            issues.append(ValidationIssue("alert_severity_known", "error", f"{alert.event_id}: unknown severity '{alert.severity}'."))
        if alert.verdict not in _KNOWN_VERDICTS:
            issues.append(ValidationIssue("alert_verdict_known", "error", f"{alert.event_id}: unknown verdict '{alert.verdict}'."))
        if alert.confidence_level not in _KNOWN_CONFIDENCE_LEVELS:
            issues.append(
                ValidationIssue("alert_confidence_level_known", "warning", f"{alert.event_id}: unusual confidenceLevel '{alert.confidence_level}'.")
            )
        if not alert.feature_contributions:
            issues.append(ValidationIssue("alert_feature_contributions_present", "warning", f"{alert.event_id}: no feature contributions attached."))
    return issues


def validate_analytics(analytics: AnalyticsData) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if len(analytics.hourly_activity) != _HOURS_IN_DAY:
        issues.append(
            ValidationIssue("analytics_hourly_completeness", "error", f"hourlyActivity has {len(analytics.hourly_activity)} entries, expected {_HOURS_IN_DAY}.")
        )
    for entry in analytics.hourly_activity:
        if entry.anomalous_events > entry.total_events:
            issues.append(ValidationIssue("analytics_hourly_bound", "error", f"hour {entry.hour}: anomalousEvents exceeds totalEvents."))
    return issues


def validate_mitre(entries: tuple[MitreEntry, ...]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if len(entries) != len(ATTACK_REGISTRY):
        issues.append(
            ValidationIssue(
                "mitre_registry_completeness",
                "error",
                f"Exported {len(entries)} MITRE entries but classification.attack_registry defines {len(ATTACK_REGISTRY)}.",
            )
        )
    known_types = {definition.attack_type.value for definition in ATTACK_REGISTRY.values()}
    for entry in entries:
        if entry.attack_type not in known_types:
            issues.append(ValidationIssue("mitre_attack_type_known", "error", f"'{entry.attack_type}' is not a registered attack type."))
    return issues


def validate_system_health(health: SystemHealthData) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for label, component in (
        ("detectionEngine", health.detection_engine),
        ("classificationEngine", health.classification_engine),
        ("explainabilityEngine", health.explainability_engine),
    ):
        if component.events_processed <= 0:
            issues.append(ValidationIssue("system_health_events_processed", "error", f"{label}: eventsProcessed must be positive."))
        if not component.last_run_id:
            issues.append(ValidationIssue("system_health_run_id_present", "error", f"{label}: lastRunId is empty."))
    return issues


def run_all_dashboard_export_validations(
    *,
    overview: OverviewMetrics,
    alerts: tuple[Alert, ...],
    analytics: AnalyticsData,
    mitre: tuple[MitreEntry, ...],
    system_health: SystemHealthData,
) -> ValidationReport:
    issues: list[ValidationIssue] = []
    issues.extend(validate_overview(overview))
    issues.extend(validate_alerts(alerts))
    issues.extend(validate_analytics(analytics))
    issues.extend(validate_mitre(mitre))
    issues.extend(validate_system_health(system_health))
    return ValidationReport(issues=tuple(issues))