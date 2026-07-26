import { useEffect, useMemo, useRef } from "react";
import { Building2, Clock, History, Laptop, MapPin } from "lucide-react";

import { BehaviourTimeline } from "@/components/dashboard/BehaviourTimeline";
import { ExplainabilityPanel } from "@/components/dashboard/ExplainabilityPanel";
import { MitrePanel } from "@/components/dashboard/MitrePanel";
import { ConfidenceBadge, SeverityBadge } from "@/components/dashboard/SeverityBadge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/Select";
import { Separator } from "@/components/ui/Separator";
import { Sheet, SheetContent } from "@/components/ui/Sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/Tabs";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/Tooltip";
import { useAlertStatus } from "@/hooks/useAlertStatus";
import { useAlerts } from "@/hooks/useDashboardData";
import { formatConfidence, formatDateTime, formatRiskScore, titleCase } from "@/lib/format";
import type { Alert, AlertStatus } from "@/types/dashboard";

export interface AlertDetailsPanelProps {
  alert: Alert | null;
  onClose: () => void;
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 py-1.5 text-sm">
      <span className="text-slate-500">{label}</span>
      <span className="font-medium text-primary">{value}</span>
    </div>
  );
}

function OverviewTab({ alert }: { alert: Alert }) {
  const { data: allAlerts } = useAlerts();

  const deviceHistory = useMemo(() => {
    const counts = new Map<string, number>();
    alert.history.forEach((event) => counts.set(event.deviceFingerprint, (counts.get(event.deviceFingerprint) ?? 0) + 1));
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [alert.history]);

  const geoHistory = useMemo(() => {
    const counts = new Map<string, number>();
    alert.history.forEach((event) => counts.set(event.geoLocation, (counts.get(event.geoLocation) ?? 0) + 1));
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [alert.history]);

  const previousAlerts = useMemo(
    () => (allAlerts ?? []).filter((other) => other.entityId === alert.entityId && other.eventId !== alert.eventId),
    [allAlerts, alert.entityId, alert.eventId],
  );

  return (
    <div className="space-y-6">
      <section aria-labelledby="entity-information-heading">
        <h3 id="entity-information-heading" className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary">
          <Building2 className="h-4 w-4 text-accent" aria-hidden="true" />
          Entity Information
        </h3>
        <div className="rounded-md border border-slate-200 p-4">
          <InfoRow label="Entity ID" value={alert.entityId} />
          <InfoRow label="Entity type" value={titleCase(alert.entityType ?? "unknown")} />
          <InfoRow label="Department" value={alert.department ?? "—"} />
          <InfoRow label="Role" value={alert.role ?? "—"} />
          <InfoRow label="Home location" value={alert.homeLocation ?? "—"} />
          <InfoRow label="Timezone" value={alert.timezone ?? "—"} />
        </div>
      </section>

      <section aria-labelledby="session-history-heading">
        <h3 id="session-history-heading" className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary">
          <Clock className="h-4 w-4 text-accent" aria-hidden="true" />
          Session History
        </h3>
        <div className="max-h-56 overflow-y-auto rounded-md border border-slate-200">
          <ul className="divide-y divide-slate-100">
            {alert.history.map((event, index) => (
              <li key={`${event.timestamp}-${index}`} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                <div className="min-w-0">
                  <p className="truncate font-medium text-primary">{event.resourceAccessed}</p>
                  <p className="text-xs text-slate-400">{formatDateTime(event.timestamp)}</p>
                </div>
                <div className="flex-shrink-0 text-right text-xs text-slate-500">
                  <p>{event.sessionDuration.toFixed(0)}s · {event.authMethod}</p>
                  <p className={event.loginResult === "failure" ? "text-red-500" : "text-emerald-600"}>
                    {titleCase(event.loginResult)}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <section aria-labelledby="device-history-heading">
          <h3 id="device-history-heading" className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary">
            <Laptop className="h-4 w-4 text-accent" aria-hidden="true" />
            Device History
          </h3>
          <ul className="space-y-1.5 rounded-md border border-slate-200 p-3">
            {deviceHistory.map(([device, count]) => (
              <li key={device} className="flex items-center justify-between gap-2 text-xs">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="truncate font-mono text-slate-600">{device.slice(0, 16)}…</span>
                  </TooltipTrigger>
                  <TooltipContent>{device}</TooltipContent>
                </Tooltip>
                <span className="flex-shrink-0 font-medium text-primary">{count}×</span>
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="geo-history-heading">
          <h3 id="geo-history-heading" className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary">
            <MapPin className="h-4 w-4 text-accent" aria-hidden="true" />
            Geo History
          </h3>
          <ul className="space-y-1.5 rounded-md border border-slate-200 p-3">
            {geoHistory.map(([location, count]) => (
              <li key={location} className="flex items-center justify-between gap-2 text-xs">
                <span className="truncate text-slate-600">{location}</span>
                <span className="flex-shrink-0 font-medium text-primary">{count}×</span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section aria-labelledby="previous-alerts-heading">
        <h3 id="previous-alerts-heading" className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary">
          <History className="h-4 w-4 text-accent" aria-hidden="true" />
          Previous Alerts for This Entity
        </h3>
        {previousAlerts.length === 0 ? (
          <p className="rounded-md border border-dashed border-slate-200 p-4 text-sm text-slate-400">
            No other alerts for {alert.entityId} in the current alert set.
          </p>
        ) : (
          <ul className="divide-y divide-slate-100 rounded-md border border-slate-200">
            {previousAlerts.map((previous) => (
              <li key={previous.eventId} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                <div>
                  <p className="font-medium text-primary">{previous.attackDisplayName}</p>
                  <p className="text-xs text-slate-400">{formatDateTime(previous.timestamp)}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-primary">{formatRiskScore(previous.riskScore)}</span>
                  <SeverityBadge severity={previous.severity} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function StatusSelect({ eventId }: { eventId: string }) {
  const { status, setStatus } = useAlertStatus(eventId);

  return (
    <Select value={status} onValueChange={(value) => setStatus(value as AlertStatus)}>
      <SelectTrigger className="w-44" aria-label="Update alert status">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="open">Open</SelectItem>
        <SelectItem value="investigating">Investigating</SelectItem>
        <SelectItem value="resolved">Resolved</SelectItem>
        <SelectItem value="false_positive">False Positive</SelectItem>
      </SelectContent>
    </Select>
  );
}

export function AlertDetailsPanel({ alert, onClose }: AlertDetailsPanelProps) {
  // Radix's Dialog only auto-restores focus to a `DialogTrigger` element.
  // This panel is opened from many different callers (table rows, preview
  // list buttons, etc.) via external state rather than a Trigger, so the
  // element that had focus at open time is captured explicitly and
  // restored on close via `onCloseAutoFocus` below — otherwise focus falls
  // back to <body>, stranding keyboard users after closing the panel.
  const triggerRef = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (alert) {
      triggerRef.current = document.activeElement as HTMLElement;
    }
  }, [alert]);

  return (
    <Sheet open={alert !== null} onOpenChange={(open) => !open && onClose()}>
      {alert ? (
        <SheetContent
          title={alert.entityId}
          description={`${alert.attackDisplayName} · ${alert.eventId}`}
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            triggerRef.current?.focus();
          }}
        >
          <div className="mb-5 flex flex-wrap items-center gap-3">
            <span className="text-2xl font-semibold text-primary">{formatRiskScore(alert.riskScore)}</span>
            <span className="text-xs text-slate-400">/ 100 risk score</span>
            <SeverityBadge severity={alert.severity} />
            <ConfidenceBadge level={alert.confidenceLevel} />
            <span className="text-xs text-slate-400">{formatConfidence(alert.confidence)} confidence</span>
            <div className="ml-auto">
              <StatusSelect eventId={alert.eventId} />
            </div>
          </div>

          <Separator className="mb-5" />

          <Tabs defaultValue="overview">
            <TabsList aria-label="Alert detail sections">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="explainability">Explainability</TabsTrigger>
              <TabsTrigger value="timeline">Timeline</TabsTrigger>
              <TabsTrigger value="mitre">MITRE ATT&amp;CK</TabsTrigger>
            </TabsList>

            <TabsContent value="overview">
              <OverviewTab alert={alert} />
            </TabsContent>
            <TabsContent value="explainability">
              <ExplainabilityPanel alert={alert} />
            </TabsContent>
            <TabsContent value="timeline">
              <BehaviourTimeline alert={alert} />
            </TabsContent>
            <TabsContent value="mitre">
              <MitrePanel alert={alert} />
            </TabsContent>
          </Tabs>
        </SheetContent>
      ) : null}
    </Sheet>
  );
}