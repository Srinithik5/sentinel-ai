import { Badge } from "@/components/ui/Badge";
import type { BadgeVariant } from "@/components/ui/Badge";
import { ALERT_STATUS_LABELS } from "@/hooks/useAlertStatus";
import { titleCase } from "@/lib/format";
import type { AlertStatus, ConfidenceLevel, Severity } from "@/types/dashboard";

const SEVERITY_VARIANT: Record<Severity, BadgeVariant> = {
  informational: "neutral",
  low: "neutral",
  medium: "warning",
  high: "danger",
  critical: "danger",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <Badge variant={SEVERITY_VARIANT[severity]} className={severity === "critical" ? "ring-1 ring-red-300" : undefined}>
      {titleCase(severity)}
    </Badge>
  );
}

const CONFIDENCE_VARIANT: Record<ConfidenceLevel, BadgeVariant> = {
  low: "neutral",
  medium: "accent",
  high: "success",
};

export function ConfidenceBadge({ level }: { level: ConfidenceLevel }) {
  return <Badge variant={CONFIDENCE_VARIANT[level]}>{titleCase(level)}</Badge>;
}

const STATUS_VARIANT: Record<AlertStatus, BadgeVariant> = {
  open: "danger",
  investigating: "warning",
  resolved: "success",
  false_positive: "neutral",
};

export function AlertStatusBadge({ status }: { status: AlertStatus }) {
  return <Badge variant={STATUS_VARIANT[status]}>{ALERT_STATUS_LABELS[status]}</Badge>;
}