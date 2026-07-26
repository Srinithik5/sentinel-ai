import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ChartCard } from "@/components/analytics/ChartCard";
import { theme } from "@/config/theme";
import { useAnalytics } from "@/hooks/useDashboardData";
import { titleCase } from "@/lib/format";
import type { Severity } from "@/types/dashboard";

const CATEGORICAL_PALETTE = ["#00C2A8", "#001F3F", "#2563EB", "#D97706", "#DC2626", "#7C3AED", "#0891B2", "#65A30D"];

const SEVERITY_COLORS: Record<Severity, string> = {
  informational: "#94a3b8",
  low: "#64748b",
  medium: "#d97706",
  high: "#ea580c",
  critical: "#dc2626",
};

const tooltipStyle = { borderRadius: 8, borderColor: "#e2e8f0", fontSize: 12 };

export function AttackDistributionChart() {
  const { data, isLoading, isError, error } = useAnalytics();
  const chartData = data?.attackDistribution.map((entry) => ({ ...entry, name: titleCase(entry.label) })) ?? [];

  return (
    <ChartCard
      title="Attack Distribution"
      description="Classified alerts by attack type"
      isLoading={isLoading}
      isError={isError}
      errorMessage={error?.message}
    >
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            dataKey="count"
            nameKey="name"
            innerRadius={55}
            outerRadius={90}
            paddingAngle={2}
          >
            {chartData.map((entry, index) => (
              <Cell key={entry.label} fill={CATEGORICAL_PALETTE[index % CATEGORICAL_PALETTE.length]} />
            ))}
          </Pie>
          <Legend verticalAlign="bottom" height={48} wrapperStyle={{ fontSize: 11 }} />
          <RechartsTooltip contentStyle={tooltipStyle} />
        </PieChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function SeverityDistributionChart() {
  const { data, isLoading, isError, error } = useAnalytics();
  const chartData = data?.severityDistribution.map((entry) => ({ ...entry, name: titleCase(entry.label) })) ?? [];

  return (
    <ChartCard
      title="Severity Distribution"
      description="Open alerts by severity level"
      isLoading={isLoading}
      isError={isError}
      errorMessage={error?.message}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
          <RechartsTooltip contentStyle={tooltipStyle} />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {chartData.map((entry) => (
              <Cell key={entry.label} fill={SEVERITY_COLORS[entry.label as Severity] ?? theme.colors.primary} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function RiskDistributionChart() {
  const { data, isLoading, isError, error } = useAnalytics();
  const chartData = data?.riskDistribution ?? [];

  return (
    <ChartCard
      title="Risk Distribution"
      description="All events by risk score band (0-100)"
      isLoading={isLoading}
      isError={isError}
      errorMessage={error?.message}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 12 }} scale="log" domain={[1, "dataMax"]} allowDataOverflow />
          <RechartsTooltip contentStyle={tooltipStyle} formatter={(value: number) => [value, "Events"]} />
          <Bar dataKey="count" fill={theme.colors.primary} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function HourlyActivityChart() {
  const { data, isLoading, isError, error } = useAnalytics();
  const chartData = data?.hourlyActivity.map((entry) => ({ ...entry, label: `${entry.hour}:00` })) ?? [];

  return (
    <ChartCard
      title="Hourly Activity"
      description="Total vs. anomalous events by hour of day"
      isLoading={isLoading}
      isError={isError}
      errorMessage={error?.message}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={2} />
          <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
          <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
          <RechartsTooltip contentStyle={tooltipStyle} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar yAxisId="left" dataKey="totalEvents" name="Total events" fill="#cbd5e1" radius={[3, 3, 0, 0]} />
          <Line yAxisId="right" type="monotone" dataKey="anomalousEvents" name="Anomalous events" stroke={theme.colors.accent} strokeWidth={2} dot={false} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function TopResourcesChart() {
  const { data, isLoading, isError, error } = useAnalytics();
  const chartData = [...(data?.topResources ?? [])].reverse();

  return (
    <ChartCard
      title="Top Resources"
      description="Most-accessed resources among flagged events"
      isLoading={isLoading}
      isError={isError}
      errorMessage={error?.message}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 12 }} allowDecimals={false} />
          <YAxis type="category" dataKey="label" width={120} tick={{ fontSize: 11 }} />
          <RechartsTooltip contentStyle={tooltipStyle} />
          <Bar dataKey="count" fill={theme.colors.accent} radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

export function GeoDistributionChart() {
  const { data, isLoading, isError, error } = useAnalytics();
  const chartData = [...(data?.geoDistribution ?? [])].reverse();

  return (
    <ChartCard
      title="Geo Distribution"
      description="Top locations among flagged events"
      isLoading={isLoading}
      isError={isError}
      errorMessage={error?.message}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 12 }} allowDecimals={false} />
          <YAxis type="category" dataKey="label" width={120} tick={{ fontSize: 11 }} />
          <RechartsTooltip contentStyle={tooltipStyle} />
          <Bar dataKey="count" fill={theme.colors.primary} radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}