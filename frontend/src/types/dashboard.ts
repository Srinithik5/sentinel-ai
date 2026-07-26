export type Severity = "informational" | "low" | "medium" | "high" | "critical";
export type Verdict = "normal" | "suspicious" | "anomalous";
export type ConfidenceLevel = "low" | "medium" | "high";
export type ActionPriority = "immediate" | "high" | "standard";
export type AlertStatus = "open" | "investigating" | "resolved" | "false_positive";

export interface DimensionDeviations {
  temporal: number;
  device: number;
  resource: number;
  geographic: number;
  authentication: number;
  session: number;
}

export interface RecommendedAction {
  priority: ActionPriority | string;
  action: string;
  rationale: string;
}

export interface AlertFeature {
  loginResult: string;
  loginHour: number;
  sessionDuration: number;
  resourceAccessed: string;
  deviceFingerprint: string;
  geoLocation: string;
  consecutiveFailures: number;
  geoVelocityKmh: number;
  authMethod: string;
  sensitiveResourceAccess: boolean;
}

export interface FeatureContribution {
  dimension: string;
  contributionPercentage: number;
  explanation: string;
}

export interface HistoryEvent {
  timestamp: string;
  resourceAccessed: string;
  deviceFingerprint: string;
  geoLocation: string;
  loginResult: string;
  sessionDuration: number;
  authMethod: string;
}

export interface ProfileBaseline {
  avgSessionDuration: number;
  sessionDurationStd: number;
  avgLoginHour: number;
  loginHourStd: number;
  sampleCount: number;
  failureRate: number;
  profileVersion: number;
  driftScore: number;
  warmupStrategy: string;
}

export interface Alert {
  eventId: string;
  entityId: string;
  entityType: string | null;
  department: string | null;
  role: string | null;
  homeLocation: string | null;
  timezone: string | null;
  timestamp: string;
  riskScore: number;
  anomalyScore: number;
  severity: Severity;
  verdict: Verdict;
  attackType: string;
  attackDisplayName: string;
  confidence: number;
  confidenceLevel: ConfidenceLevel;
  mitreTactic: string;
  mitreTechnique: string;
  dimensionDeviations: DimensionDeviations;
  topIndicators: string[];
  featureContributions: FeatureContribution[];
  evidenceSummary: string;
  confidenceExplanation: string;
  recommendedActions: RecommendedAction[];
  matchedIndicators: string[];
  feature: AlertFeature;
  history: HistoryEvent[];
  profileBaseline: ProfileBaseline | null;
}

export interface OverviewMetrics {
  totalEvents: number;
  anomalies: number;
  criticalAlerts: number;
  detectionAccuracy: number;
  averageRisk: number;
  falsePositiveRate: number;
  detectionLatencyMs: number;
  measurementNote: string;
}

export interface DistributionEntry {
  label: string;
  count: number;
}

export interface HourlyActivityEntry {
  hour: number;
  totalEvents: number;
  anomalousEvents: number;
}

export interface AnalyticsData {
  attackDistribution: DistributionEntry[];
  severityDistribution: DistributionEntry[];
  riskDistribution: DistributionEntry[];
  hourlyActivity: HourlyActivityEntry[];
  topResources: DistributionEntry[];
  geoDistribution: DistributionEntry[];
}

export interface MitreEntry {
  attackType: string;
  displayName: string;
  tactic: string;
  technique: string;
  severity: Severity;
  description: string;
}

export type EngineHealthMode = "live" | "batch" | "not_deployed";
export type EngineHealthStatus = "operational" | "degraded" | "offline";

export interface LiveHealthComponent {
  mode: "live";
  note: string;
}

export interface BatchHealthComponent {
  mode: "batch";
  status: EngineHealthStatus;
  lastRunId: string;
  lastRunPassed: boolean;
  eventsProcessed: number;
  note: string;
}

export interface NotDeployedHealthComponent {
  mode: "not_deployed";
  status: EngineHealthStatus;
  note: string;
}

export interface SystemHealthData {
  backend: LiveHealthComponent;
  database: LiveHealthComponent;
  detectionEngine: BatchHealthComponent;
  classificationEngine: BatchHealthComponent;
  explainabilityEngine: BatchHealthComponent;
  streamingPipeline: NotDeployedHealthComponent;
}

export const SEVERITY_ORDER: Severity[] = ["informational", "low", "medium", "high", "critical"];

export const DIMENSION_LABELS: Record<keyof DimensionDeviations, string> = {
  temporal: "Temporal",
  device: "Device",
  resource: "Resource",
  geographic: "Geographic",
  authentication: "Authentication",
  session: "Session",
};