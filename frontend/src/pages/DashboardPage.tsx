import { useState } from "react";
import { ArrowRight, ShieldOff } from "lucide-react";
import { Link } from "react-router-dom";

import { AlertDetailsPanel } from "@/components/dashboard/AlertDetailsPanel";
import { ExecutiveOverview } from "@/components/dashboard/ExecutiveOverview";
import { AlertStatusBadge, SeverityBadge } from "@/components/dashboard/SeverityBadge";
import { SystemHealthPanel } from "@/components/system/SystemHealthPanel";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { buttonVariants } from "@/components/ui/Button";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { useAlertStatusMap } from "@/hooks/useAlertStatus";
import { useAlerts } from "@/hooks/useDashboardData";
import { formatDateTime, formatRiskScore } from "@/lib/format";
import { ROUTES } from "@/routes/paths";
import type { Alert } from "@/types/dashboard";

const PREVIEW_COUNT = 6;

function RecentCriticalAlerts({ onSelectAlert }: { onSelectAlert: (alert: Alert) => void }) {
  const { data: alerts, isLoading, isError, error } = useAlerts();
  const statusMap = useAlertStatusMap();

  const openAlerts = (alerts ?? [])
    .filter((alert) => (statusMap[alert.eventId] ?? "open") === "open")
    .sort((a, b) => b.riskScore - a.riskScore);

  // One row per entity (its own highest-risk open alert) — an executive
  // preview should surface which entities need attention, not repeat the
  // same entity's own multi-event incident several times over.
  const seenEntities = new Set<string>();
  const preview: Alert[] = [];
  for (const alert of openAlerts) {
    if (seenEntities.has(alert.entityId)) continue;
    seenEntities.add(alert.entityId);
    preview.push(alert);
    if (preview.length >= PREVIEW_COUNT) break;
  }

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Highest-Risk Open Alerts</CardTitle>
        <Link to={ROUTES.alerts} className="flex items-center gap-1 text-xs font-medium text-accent hover:underline">
          View all <ArrowRight className="h-3 w-3" aria-hidden="true" />
        </Link>
      </CardHeader>
      <CardContent className="p-0">
        {isError ? (
          <ErrorState message={error.message} />
        ) : isLoading ? (
          <div className="space-y-3 p-5">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-10 w-full" />
            ))}
          </div>
        ) : preview.length === 0 ? (
          <EmptyState icon={ShieldOff} title="No open alerts" description="Every alert in the current set has been triaged." />
        ) : (
          <ul className="divide-y divide-slate-100">
            {preview.map((alert) => (
              <li key={alert.eventId}>
                <button
                  type="button"
                  onClick={() => onSelectAlert(alert)}
                  className="flex w-full items-center justify-between gap-3 px-5 py-3 text-left transition-colors hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-accent"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-primary">
                      {alert.entityId} · {alert.attackDisplayName}
                    </p>
                    <p className="text-xs text-slate-400">{formatDateTime(alert.timestamp)}</p>
                  </div>
                  <div className="flex flex-shrink-0 items-center gap-2">
                    <span className="text-sm font-semibold text-primary">{formatRiskScore(alert.riskScore)}</span>
                    <SeverityBadge severity={alert.severity} />
                    <AlertStatusBadge status={statusMap[alert.eventId] ?? "open"} />
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  return (
    <>
      <PageHeader
        title="SentinelAI"
        description="AI-Powered Behavioral Anomaly Detection Platform — Executive Overview"
        actions={
          <Link to={ROUTES.alerts} className={buttonVariants({ variant: "primary", size: "sm" })}>
            Open Alert Queue
          </Link>
        }
      />

      <div className="space-y-6">
        <ExecutiveOverview />

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <RecentCriticalAlerts onSelectAlert={setSelectedAlert} />
          </div>
          <SystemHealthPanel />
        </div>
      </div>

      <AlertDetailsPanel alert={selectedAlert} onClose={() => setSelectedAlert(null)} />
    </>
  );
}