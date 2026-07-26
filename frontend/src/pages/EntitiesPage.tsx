import { useMemo, useState } from "react";
import { Boxes } from "lucide-react";

import { AlertDetailsPanel } from "@/components/dashboard/AlertDetailsPanel";
import { SeverityBadge } from "@/components/dashboard/SeverityBadge";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "@/components/ui/Table";
import { useAlerts } from "@/hooks/useDashboardData";
import { formatDateTime, formatRiskScore, titleCase } from "@/lib/format";
import type { Alert, Severity } from "@/types/dashboard";
import { SEVERITY_ORDER } from "@/types/dashboard";

interface EntitySummary {
  entityId: string;
  entityType: string | null;
  department: string | null;
  alertCount: number;
  maxRisk: number;
  highestSeverity: Severity;
  lastSeen: string;
  mostRecentAlert: Alert;
}

function summarizeByEntity(alerts: Alert[]): EntitySummary[] {
  const byEntity = new Map<string, Alert[]>();
  alerts.forEach((alert) => {
    const bucket = byEntity.get(alert.entityId) ?? [];
    bucket.push(alert);
    byEntity.set(alert.entityId, bucket);
  });

  return [...byEntity.entries()]
    .map(([entityId, entityAlerts]) => {
      const sortedByTime = [...entityAlerts].sort(
        (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      );
      const highestSeverity = entityAlerts.reduce<Severity>((max, alert) => {
        return SEVERITY_ORDER.indexOf(alert.severity) > SEVERITY_ORDER.indexOf(max) ? alert.severity : max;
      }, "informational");

      return {
        entityId,
        entityType: entityAlerts[0].entityType,
        department: entityAlerts[0].department,
        alertCount: entityAlerts.length,
        maxRisk: Math.max(...entityAlerts.map((alert) => alert.riskScore)),
        highestSeverity,
        lastSeen: sortedByTime[0].timestamp,
        mostRecentAlert: sortedByTime[0],
      };
    })
    .sort((a, b) => b.maxRisk - a.maxRisk);
}

export default function EntitiesPage() {
  const { data: alerts, isLoading, isError, error } = useAlerts();
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  const entities = useMemo(() => (alerts ? summarizeByEntity(alerts) : []), [alerts]);

  return (
    <>
      <PageHeader
        title="Entities"
        description="Users, service accounts, and devices with at least one flagged alert, ranked by peak risk score."
      />

      {isError ? (
        <ErrorState title="Unable to load entities" message={error.message} />
      ) : (
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell>Entity</TableHeaderCell>
                <TableHeaderCell>Type</TableHeaderCell>
                <TableHeaderCell>Alerts</TableHeaderCell>
                <TableHeaderCell>Peak Risk</TableHeaderCell>
                <TableHeaderCell>Highest Severity</TableHeaderCell>
                <TableHeaderCell>Last Seen</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading
                ? Array.from({ length: 6 }).map((_, index) => (
                    <TableRow key={index}>
                      {Array.from({ length: 6 }).map((__, cellIndex) => (
                        <TableCell key={cellIndex}>
                          <Skeleton className="h-4 w-full max-w-[8rem]" />
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                : null}

              {!isLoading && entities.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6}>
                    <EmptyState icon={Boxes} title="No entities with alerts" description="Nothing has been flagged yet." />
                  </TableCell>
                </TableRow>
              ) : null}

              {entities.map((entity) => (
                <TableRow
                  key={entity.entityId}
                  tabIndex={0}
                  role="button"
                  aria-label={`View most recent alert for ${entity.entityId}`}
                  onClick={(event) => {
                    event.currentTarget.focus();
                    setSelectedAlert(entity.mostRecentAlert);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setSelectedAlert(entity.mostRecentAlert);
                    }
                  }}
                  className="cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-accent"
                >
                  <TableCell>
                    <div className="font-medium text-primary">{entity.entityId}</div>
                    <div className="text-xs text-slate-400">{entity.department ?? "—"}</div>
                  </TableCell>
                  <TableCell>{titleCase(entity.entityType ?? "unknown")}</TableCell>
                  <TableCell>{entity.alertCount}</TableCell>
                  <TableCell className="font-semibold text-primary">{formatRiskScore(entity.maxRisk)}</TableCell>
                  <TableCell>
                    <SeverityBadge severity={entity.highestSeverity} />
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-slate-500">{formatDateTime(entity.lastSeen)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <AlertDetailsPanel alert={selectedAlert} onClose={() => setSelectedAlert(null)} />
    </>
  );
}