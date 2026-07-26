import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, XAxis, YAxis } from "recharts";
import { CheckSquare, FileSearch, Lightbulb, ListChecks } from "lucide-react";

import { theme } from "@/config/theme";
import { titleCase } from "@/lib/format";
import type { Alert } from "@/types/dashboard";

const PRIORITY_STYLES: Record<string, string> = {
  immediate: "border-red-200 bg-red-50 text-red-700",
  high: "border-amber-200 bg-amber-50 text-amber-700",
  standard: "border-slate-200 bg-slate-50 text-slate-600",
};

export function ExplainabilityPanel({ alert }: { alert: Alert }) {
  const chartData = [...alert.featureContributions]
    .sort((a, b) => b.contributionPercentage - a.contributionPercentage)
    .map((entry) => ({ ...entry, name: titleCase(entry.dimension) }));

  return (
    <div className="space-y-6">
      <section aria-labelledby="feature-contribution-heading">
        <h3 id="feature-contribution-heading" className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary">
          <ListChecks className="h-4 w-4 text-accent" aria-hidden="true" />
          Top Features &amp; Feature Contribution
        </h3>
        <div className="rounded-md border border-slate-200 p-4">
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                <XAxis type="number" domain={[0, "dataMax"]} tickFormatter={(value: number) => `${value}%`} tick={{ fontSize: 12 }} />
                <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 12 }} />
                <RechartsTooltip
                  formatter={(value: number) => [`${value}%`, "Contribution"]}
                  contentStyle={{ borderRadius: 8, borderColor: "#e2e8f0", fontSize: 12 }}
                />
                <Bar dataKey="contributionPercentage" radius={[0, 4, 4, 0]}>
                  {chartData.map((entry) => (
                    <Cell key={entry.dimension} fill={entry === chartData[0] ? theme.colors.accent : "#94a3b8"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <ul className="mt-3 space-y-2">
            {chartData.map((entry) => (
              <li key={entry.dimension} className="text-sm">
                <span className="font-medium text-primary">
                  {entry.name} ({entry.contributionPercentage.toFixed(1)}%):
                </span>{" "}
                <span className="text-slate-500">{entry.explanation}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section aria-labelledby="evidence-heading">
        <h3 id="evidence-heading" className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary">
          <FileSearch className="h-4 w-4 text-accent" aria-hidden="true" />
          Evidence
        </h3>
        {alert.matchedIndicators.length === 0 ? (
          <p className="rounded-md border border-dashed border-slate-200 p-4 text-sm text-slate-400">
            No specific classification indicators matched strongly enough for this event.
          </p>
        ) : (
          <ul className="space-y-1.5 rounded-md border border-slate-200 p-4">
            {alert.matchedIndicators.map((indicator, index) => (
              <li key={index} className="flex items-start gap-2 text-sm text-slate-600">
                <CheckSquare className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-accent" aria-hidden="true" />
                <span>{indicator}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="reason-heading">
        <h3 id="reason-heading" className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary">
          <Lightbulb className="h-4 w-4 text-accent" aria-hidden="true" />
          Reason
        </h3>
        <p className="rounded-md border border-slate-200 p-4 text-sm leading-relaxed text-slate-600">
          {alert.evidenceSummary}
        </p>
        <p className="mt-3 rounded-md bg-slate-50 p-4 text-sm leading-relaxed text-slate-600">
          {alert.confidenceExplanation}
        </p>
      </section>

      <section aria-labelledby="recommendation-heading">
        <h3 id="recommendation-heading" className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary">
          <ListChecks className="h-4 w-4 text-accent" aria-hidden="true" />
          Recommendation
        </h3>
        <ul className="space-y-2">
          {alert.recommendedActions.map((action, index) => (
            <li
              key={index}
              className={`rounded-md border px-3 py-2 text-sm ${PRIORITY_STYLES[action.priority] ?? PRIORITY_STYLES.standard}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{action.action}</span>
                <span className="flex-shrink-0 text-xs uppercase tracking-wide opacity-75">{action.priority}</span>
              </div>
              {action.rationale ? <p className="mt-0.5 text-xs opacity-80">{action.rationale}</p> : null}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}