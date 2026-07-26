import { Activity, AlertOctagon, Gauge, ShieldAlert, Target, Timer, TrendingDown } from "lucide-react";

import { MetricCard } from "@/components/ui/MetricCard";
import { ErrorState } from "@/components/ui/EmptyState";
import { useOverviewMetrics } from "@/hooks/useDashboardData";
import { formatNumber, formatPercent, formatRiskScore } from "@/lib/format";

export function ExecutiveOverview() {
  const { data, isLoading, isError, error } = useOverviewMetrics();

  if (isError) {
    return <ErrorState title="Unable to load overview metrics" message={error.message} />;
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <MetricCard
        label="Total Events"
        value={data ? formatNumber(data.totalEvents) : undefined}
        icon={Activity}
        tone="neutral"
        helpText="Phase 2 + 2B generated event volume"
        loading={isLoading}
      />
      <MetricCard
        label="Anomalies"
        value={data ? formatNumber(data.anomalies) : undefined}
        icon={ShieldAlert}
        tone="warning"
        helpText={data ? `${formatPercent((data.anomalies / data.totalEvents) * 100, 2)} of all events` : undefined}
        loading={isLoading}
      />
      <MetricCard
        label="Critical Alerts"
        value={data ? formatNumber(data.criticalAlerts) : undefined}
        icon={AlertOctagon}
        tone="danger"
        helpText="Severity = Critical, open triage"
        loading={isLoading}
      />
      <MetricCard
        label="Detection Accuracy"
        value={data ? formatPercent(data.detectionAccuracy, 2) : undefined}
        icon={Target}
        tone="success"
        helpText="Retrospective, vs. ground truth"
        loading={isLoading}
      />
      <MetricCard
        label="Average Risk"
        value={data ? formatRiskScore(data.averageRisk) : undefined}
        icon={Gauge}
        tone="accent"
        helpText="Mean risk score across open alerts (0-100)"
        loading={isLoading}
      />
      <MetricCard
        label="False Positive Rate"
        value={data ? formatPercent(data.falsePositiveRate, 1) : undefined}
        icon={TrendingDown}
        tone="warning"
        helpText="Share of flagged alerts without a matching attack"
        loading={isLoading}
      />
      <MetricCard
        label="Detection Latency"
        value={data ? `${data.detectionLatencyMs.toFixed(2)} ms` : undefined}
        icon={Timer}
        tone="accent"
        helpText="Avg. per-event processing time, measured live"
        loading={isLoading}
      />
    </div>
  );
}