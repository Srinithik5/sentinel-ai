import { useState } from "react";
import { motion } from "framer-motion";
import { ChevronDown, GitCommitHorizontal } from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";

import { theme } from "@/config/theme";
import { formatDateTime, titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Alert } from "@/types/dashboard";

function HistoricalComparisonChart({ alert }: { alert: Alert }) {
  const baseline = alert.profileBaseline;
  const chartData = alert.history.map((event, index) => ({
    index,
    label: formatDateTime(event.timestamp),
    sessionDuration: event.sessionDuration,
  }));

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="index" tick={false} label={{ value: "Session sequence →", position: "insideBottom", offset: -2, fontSize: 11, fill: "#94a3b8" }} />
          <YAxis tick={{ fontSize: 11 }} width={40} label={{ value: "Duration (s)", angle: -90, position: "insideLeft", fontSize: 11, fill: "#94a3b8" }} />
          <RechartsTooltip
            labelFormatter={() => ""}
            formatter={(value: number) => [`${value.toFixed(0)}s`, "Session duration"]}
            contentStyle={{ borderRadius: 8, borderColor: "#e2e8f0", fontSize: 12 }}
          />
          {baseline ? (
            <ReferenceArea
              y1={Math.max(0, baseline.avgSessionDuration - baseline.sessionDurationStd)}
              y2={baseline.avgSessionDuration + baseline.sessionDurationStd}
              fill={theme.colors.accent}
              fillOpacity={0.08}
            />
          ) : null}
          {baseline ? (
            <ReferenceLine
              y={baseline.avgSessionDuration}
              stroke={theme.colors.accent}
              strokeDasharray="4 4"
              label={{ value: "Baseline avg", position: "insideTopRight", fontSize: 11, fill: theme.colors.accent }}
            />
          ) : null}
          <Line type="monotone" dataKey="sessionDuration" stroke={theme.colors.primary} strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function SessionSequence({ alert }: { alert: Alert }) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(alert.history.length - 1);

  return (
    <ol className="relative space-y-0 border-l border-slate-200 pl-6">
      {alert.history.map((event, index) => {
        const isFlaggedEvent = index === alert.history.length - 1;
        const isExpanded = expandedIndex === index;
        return (
          <li key={`${event.timestamp}-${index}`} className="relative pb-4 last:pb-0">
            <span
              className={cn(
                "absolute -left-[29px] flex h-4 w-4 items-center justify-center rounded-full border-2 border-white",
                isFlaggedEvent ? "bg-red-500" : "bg-accent",
              )}
              aria-hidden="true"
            />
            <button
              type="button"
              onClick={() => setExpandedIndex(isExpanded ? null : index)}
              aria-expanded={isExpanded}
              className="flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-primary">
                  {event.resourceAccessed}
                  {isFlaggedEvent ? <span className="ml-2 text-xs font-semibold text-red-500">FLAGGED EVENT</span> : null}
                </p>
                <p className="text-xs text-slate-400">{formatDateTime(event.timestamp)}</p>
              </div>
              <ChevronDown
                className={cn("h-4 w-4 flex-shrink-0 text-slate-400 transition-transform", isExpanded && "rotate-180")}
                aria-hidden="true"
              />
            </button>
            {isExpanded ? (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                transition={{ duration: 0.15 }}
                className="overflow-hidden px-2"
              >
                <dl className="mt-1 grid grid-cols-2 gap-x-4 gap-y-1 rounded-md bg-slate-50 p-3 text-xs">
                  <dt className="text-slate-400">Device</dt>
                  <dd className="truncate font-mono text-slate-600">{event.deviceFingerprint.slice(0, 20)}…</dd>
                  <dt className="text-slate-400">Location</dt>
                  <dd className="text-slate-600">{event.geoLocation}</dd>
                  <dt className="text-slate-400">Auth method</dt>
                  <dd className="text-slate-600">{titleCase(event.authMethod)}</dd>
                  <dt className="text-slate-400">Result</dt>
                  <dd className={event.loginResult === "failure" ? "text-red-500" : "text-emerald-600"}>
                    {titleCase(event.loginResult)}
                  </dd>
                  <dt className="text-slate-400">Session duration</dt>
                  <dd className="text-slate-600">{event.sessionDuration.toFixed(0)}s</dd>
                </dl>
              </motion.div>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}

export function BehaviourTimeline({ alert }: { alert: Alert }) {
  return (
    <div className="space-y-6">
      <section aria-labelledby="historical-comparison-heading">
        <h3 id="historical-comparison-heading" className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary">
          <GitCommitHorizontal className="h-4 w-4 text-accent" aria-hidden="true" />
          Historical Comparison
        </h3>
        <div className="rounded-md border border-slate-200 p-4">
          {alert.profileBaseline ? (
            <HistoricalComparisonChart alert={alert} />
          ) : (
            <p className="py-8 text-center text-sm text-slate-400">
              No behaviour profile baseline is available for this entity yet.
            </p>
          )}
        </div>
      </section>

      <section aria-labelledby="session-sequence-heading">
        <h3 id="session-sequence-heading" className="mb-2 text-sm font-semibold text-primary">
          Session Sequence
        </h3>
        <p className="mb-3 text-xs text-slate-400">
          The {alert.history.length} most recent events for {alert.entityId} leading up to and including the flagged
          event. Select any entry to expand its detail.
        </p>
        <SessionSequence alert={alert} />
      </section>
    </div>
  );
}