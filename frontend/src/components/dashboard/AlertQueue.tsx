import { ArrowDown, ArrowUp, ArrowUpDown, Search, ShieldAlert } from "lucide-react";
import { useMemo, useState } from "react";

import { AlertStatusBadge, ConfidenceBadge, SeverityBadge } from "@/components/dashboard/SeverityBadge";
import { Card } from "@/components/ui/Card";
import { EmptyState, ErrorState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Pagination } from "@/components/ui/Pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/Select";
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
import { useAlertStatusMap } from "@/hooks/useAlertStatus";
import { useAlerts } from "@/hooks/useDashboardData";
import { formatConfidence, formatDateTime, formatRiskScore, titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";
import { SEVERITY_ORDER } from "@/types/dashboard";
import type { Alert, AlertStatus, Severity } from "@/types/dashboard";

type SortKey = "timestamp" | "riskScore" | "confidence";
type SortDirection = "asc" | "desc";

const PAGE_SIZE = 25;

export interface AlertQueueProps {
  onSelectAlert: (alert: Alert) => void;
}

export function AlertQueue({ onSelectAlert }: AlertQueueProps) {
  const { data: alerts, isLoading, isError, error } = useAlerts();
  const statusMap = useAlertStatusMap();

  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState<Severity | "all">("all");
  const [attackFilter, setAttackFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<AlertStatus | "all">("all");
  const [sortKey, setSortKey] = useState<SortKey>("riskScore");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [page, setPage] = useState(1);

  const attackTypes = useMemo(() => {
    if (!alerts) return [];
    return [...new Set(alerts.map((alert) => alert.attackType))].sort();
  }, [alerts]);

  const filtered = useMemo(() => {
    if (!alerts) return [];
    const query = search.trim().toLowerCase();

    const rows = alerts.filter((alert) => {
      const status = statusMap[alert.eventId] ?? "open";
      if (severityFilter !== "all" && alert.severity !== severityFilter) return false;
      if (attackFilter !== "all" && alert.attackType !== attackFilter) return false;
      if (statusFilter !== "all" && status !== statusFilter) return false;
      if (!query) return true;
      return (
        alert.entityId.toLowerCase().includes(query) ||
        alert.eventId.toLowerCase().includes(query) ||
        alert.attackDisplayName.toLowerCase().includes(query) ||
        alert.mitreTechnique.toLowerCase().includes(query)
      );
    });

    const sorted = [...rows].sort((a, b) => {
      let comparison = 0;
      if (sortKey === "timestamp") {
        comparison = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
      } else if (sortKey === "riskScore") {
        comparison = a.riskScore - b.riskScore;
      } else {
        comparison = a.confidence - b.confidence;
      }
      return sortDirection === "asc" ? comparison : -comparison;
    });

    return sorted;
  }, [alerts, search, severityFilter, attackFilter, statusFilter, sortKey, sortDirection, statusMap]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const pageRows = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDirection("desc");
    }
    setPage(1);
  }

  function SortIcon({ column }: { column: SortKey }) {
    if (sortKey !== column) return <ArrowUpDown className="h-3 w-3 text-slate-300" aria-hidden="true" />;
    return sortDirection === "asc" ? (
      <ArrowUp className="h-3 w-3 text-accent" aria-hidden="true" />
    ) : (
      <ArrowDown className="h-3 w-3 text-accent" aria-hidden="true" />
    );
  }

  if (isError) {
    return <ErrorState title="Unable to load the alert queue" message={error.message} />;
  }

  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col gap-3 border-b border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="w-full max-w-sm">
          <Input
            type="search"
            placeholder="Search entity, event ID, attack, or technique"
            leadingIcon={Search}
            aria-label="Search alerts"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Select
            value={severityFilter}
            onValueChange={(value) => {
              setSeverityFilter(value as Severity | "all");
              setPage(1);
            }}
          >
            <SelectTrigger className="w-40" aria-label="Filter by severity">
              <SelectValue placeholder="Severity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All severities</SelectItem>
              {SEVERITY_ORDER.map((severity) => (
                <SelectItem key={severity} value={severity}>
                  {titleCase(severity)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={attackFilter}
            onValueChange={(value) => {
              setAttackFilter(value);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-48" aria-label="Filter by attack type">
              <SelectValue placeholder="Attack type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All attack types</SelectItem>
              {attackTypes.map((type) => (
                <SelectItem key={type} value={type}>
                  {titleCase(type)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select
            value={statusFilter}
            onValueChange={(value) => {
              setStatusFilter(value as AlertStatus | "all");
              setPage(1);
            }}
          >
            <SelectTrigger className="w-40" aria-label="Filter by status">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="open">Open</SelectItem>
              <SelectItem value="investigating">Investigating</SelectItem>
              <SelectItem value="resolved">Resolved</SelectItem>
              <SelectItem value="false_positive">False Positive</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <TableContainer className="rounded-none border-none">
        <Table>
          <TableHead>
            <TableRow>
              <TableHeaderCell>
                <button
                  type="button"
                  onClick={() => toggleSort("timestamp")}
                  className="flex items-center gap-1 uppercase tracking-wide"
                >
                  Timestamp <SortIcon column="timestamp" />
                </button>
              </TableHeaderCell>
              <TableHeaderCell>Entity</TableHeaderCell>
              <TableHeaderCell>
                <button
                  type="button"
                  onClick={() => toggleSort("riskScore")}
                  className="flex items-center gap-1 uppercase tracking-wide"
                >
                  Risk <SortIcon column="riskScore" />
                </button>
              </TableHeaderCell>
              <TableHeaderCell>Attack</TableHeaderCell>
              <TableHeaderCell>
                <button
                  type="button"
                  onClick={() => toggleSort("confidence")}
                  className="flex items-center gap-1 uppercase tracking-wide"
                >
                  Confidence <SortIcon column="confidence" />
                </button>
              </TableHeaderCell>
              <TableHeaderCell>Severity</TableHeaderCell>
              <TableHeaderCell>Status</TableHeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading
              ? Array.from({ length: 8 }).map((_, index) => (
                  <TableRow key={index}>
                    {Array.from({ length: 7 }).map((__, cellIndex) => (
                      <TableCell key={cellIndex}>
                        <Skeleton className="h-4 w-full max-w-[8rem]" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              : null}

            {!isLoading && pageRows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7}>
                  <EmptyState
                    icon={ShieldAlert}
                    title="No alerts match these filters"
                    description="Try clearing the search text or resetting a filter."
                  />
                </TableCell>
              </TableRow>
            ) : null}

            {pageRows.map((alert) => {
              const status = statusMap[alert.eventId] ?? "open";
              return (
                <TableRow
                  key={alert.eventId}
                  tabIndex={0}
                  role="button"
                  aria-label={`View details for alert on ${alert.entityId}`}
                  onClick={(event) => {
                    // Radix Dialog restores focus to whatever element was
                    // focused when it opened. A <tr> doesn't always receive
                    // focus on a plain mouse click the way a <button> does,
                    // so it's focused explicitly here to keep keyboard
                    // users landed back on this row after closing the panel.
                    event.currentTarget.focus();
                    onSelectAlert(alert);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelectAlert(alert);
                    }
                  }}
                  className={cn("cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-accent")}
                >
                  <TableCell className="whitespace-nowrap text-slate-500">{formatDateTime(alert.timestamp)}</TableCell>
                  <TableCell>
                    <div className="font-medium text-primary">{alert.entityId}</div>
                    <div className="text-xs text-slate-400">{alert.department ?? alert.entityType}</div>
                  </TableCell>
                  <TableCell>
                    <span className="font-semibold text-primary">{formatRiskScore(alert.riskScore)}</span>
                  </TableCell>
                  <TableCell>{alert.attackDisplayName}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <span>{formatConfidence(alert.confidence)}</span>
                      <ConfidenceBadge level={alert.confidenceLevel} />
                    </div>
                  </TableCell>
                  <TableCell>
                    <SeverityBadge severity={alert.severity} />
                  </TableCell>
                  <TableCell>
                    <AlertStatusBadge status={status} />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      <div className="flex items-center justify-between gap-4 px-4 py-2 text-xs text-slate-400">
        <span>
          Showing {pageRows.length === 0 ? 0 : (currentPage - 1) * PAGE_SIZE + 1}-
          {(currentPage - 1) * PAGE_SIZE + pageRows.length} of {filtered.length} alerts
        </span>
      </div>
      <Pagination page={currentPage} pageCount={pageCount} onPageChange={setPage} />
    </Card>
  );
}