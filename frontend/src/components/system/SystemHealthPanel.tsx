import { CheckCircle2, Database, Server, ShieldCheck, Sparkles, Workflow } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { BadgeVariant } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { useHealthQuery } from "@/hooks/useHealthQuery";
import { useSystemHealth } from "@/hooks/useDashboardData";
import { formatNumber } from "@/lib/format";
import type { BatchHealthComponent, NotDeployedHealthComponent } from "@/types/dashboard";

interface ComponentRowProps {
  icon: LucideIcon;
  label: string;
  statusLabel: string;
  tone: BadgeVariant;
  detail: string;
}

function ComponentRow({ icon: Icon, label, statusLabel, tone, detail }: ComponentRowProps) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-100 py-3 last:border-b-0">
      <div className="flex items-start gap-3">
        <Icon className="mt-0.5 h-4 w-4 flex-shrink-0 text-slate-400" aria-hidden="true" />
        <div>
          <p className="text-sm font-medium text-primary">{label}</p>
          <p className="text-xs text-slate-500">{detail}</p>
        </div>
      </div>
      <Badge variant={tone} className="flex-shrink-0">
        {statusLabel}
      </Badge>
    </div>
  );
}

function batchDetail(component: BatchHealthComponent): string {
  return `${component.note} Last run ${component.lastRunId} processed ${formatNumber(component.eventsProcessed)} events.`;
}

export function SystemHealthPanel() {
  const health = useHealthQuery();
  const system = useSystemHealth();

  if (system.isError) {
    return <ErrorState title="Unable to load system health" message={system.error.message} />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>System Health</CardTitle>
      </CardHeader>
      <CardContent aria-live="polite">
        {system.isLoading || !system.data ? (
          <div className="space-y-3 py-2">
            {Array.from({ length: 6 }).map((_, index) => (
              <Skeleton key={index} className="h-10 w-full" />
            ))}
          </div>
        ) : (
          <div>
            <ComponentRow
              icon={Server}
              label="Backend"
              statusLabel={
                health.isLoading
                  ? "Checking…"
                  : health.isError || health.data?.status !== "healthy"
                    ? "Unavailable"
                    : "Healthy"
              }
              tone={
                health.isLoading
                  ? "neutral"
                  : health.isError || health.data?.status !== "healthy"
                    ? "danger"
                    : "success"
              }
              detail={system.data.backend.note}
            />
            <ComponentRow
              icon={Database}
              label="Database"
              statusLabel={
                health.isLoading
                  ? "Checking…"
                  : health.data?.database === "connected"
                    ? "Connected"
                    : "Disconnected"
              }
              tone={health.isLoading ? "neutral" : health.data?.database === "connected" ? "success" : "danger"}
              detail={system.data.database.note}
            />
            <ComponentRow
              icon={ShieldCheck}
              label="Detection Engine"
              statusLabel={system.data.detectionEngine.lastRunPassed ? "Operational" : "Failing"}
              tone={system.data.detectionEngine.lastRunPassed ? "success" : "danger"}
              detail={batchDetail(system.data.detectionEngine)}
            />
            <ComponentRow
              icon={Sparkles}
              label="Classification Engine"
              statusLabel={system.data.classificationEngine.lastRunPassed ? "Operational" : "Failing"}
              tone={system.data.classificationEngine.lastRunPassed ? "success" : "danger"}
              detail={batchDetail(system.data.classificationEngine)}
            />
            <ComponentRow
              icon={CheckCircle2}
              label="Explainability Engine"
              statusLabel={system.data.explainabilityEngine.lastRunPassed ? "Operational" : "Failing"}
              tone={system.data.explainabilityEngine.lastRunPassed ? "success" : "danger"}
              detail={batchDetail(system.data.explainabilityEngine)}
            />
            <ComponentRow
              icon={Workflow}
              label="Streaming Pipeline"
              statusLabel="Not Deployed"
              tone="neutral"
              detail={(system.data.streamingPipeline as NotDeployedHealthComponent).note}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}