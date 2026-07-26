import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Card, CardContent } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { cn } from "@/lib/utils";

export type MetricTone = "neutral" | "success" | "warning" | "danger" | "accent";

const TONE_STYLES: Record<MetricTone, string> = {
  neutral: "bg-slate-100 text-slate-600",
  success: "bg-emerald-100 text-emerald-700",
  warning: "bg-amber-100 text-amber-700",
  danger: "bg-red-100 text-red-700",
  accent: "bg-accent/10 text-accent",
};

export interface MetricCardProps {
  label: string;
  value: ReactNode;
  icon: LucideIcon;
  tone?: MetricTone;
  helpText?: string;
  loading?: boolean;
}

export function MetricCard({ label, value, icon: Icon, tone = "neutral", helpText, loading = false }: MetricCardProps) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between gap-4 p-5">
        <div className="min-w-0 space-y-1.5">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
          {loading ? (
            <Skeleton className="h-7 w-20" />
          ) : (
            <p className="truncate text-2xl font-semibold text-primary">{value}</p>
          )}
          {helpText ? <p className="text-xs text-slate-400">{helpText}</p> : null}
        </div>
        <div className={cn("flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg", TONE_STYLES[tone])}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
      </CardContent>
    </Card>
  );
}