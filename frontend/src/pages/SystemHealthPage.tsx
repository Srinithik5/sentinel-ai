import { Activity, Gauge, Target, Timer } from "lucide-react";

import { SystemHealthPanel } from "@/components/system/SystemHealthPanel";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { useOverviewMetrics } from "@/hooks/useDashboardData";
import { formatNumber, formatPercent } from "@/lib/format";

function PipelineStat({ label, value, icon: Icon }: { label: string; value: string; icon: typeof Activity }) {
  return (
    <div className="flex items-center gap-3 rounded-md border border-slate-200 p-4">
      <Icon className="h-5 w-5 flex-shrink-0 text-accent" aria-hidden="true" />
      <div>
        <p className="text-xs text-slate-500">{label}</p>
        <p className="text-lg font-semibold text-primary">{value}</p>
      </div>
    </div>
  );
}

export default function SystemHealthPage() {
  const { data, isLoading, isError, error } = useOverviewMetrics();

  return (
    <>
      <PageHeader
        title="System Health"
        description="Live web service status plus the last verified run of every AI engine pipeline stage."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <SystemHealthPanel />
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Last Verified Pipeline Run</CardTitle>
          </CardHeader>
          <CardContent>
            {isError ? (
              <ErrorState message={error.message} />
            ) : isLoading || !data ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, index) => (
                  <Skeleton key={index} className="h-14 w-full" />
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                <PipelineStat label="Events processed" value={formatNumber(data.totalEvents)} icon={Activity} />
                <PipelineStat label="Detection accuracy" value={formatPercent(data.detectionAccuracy, 2)} icon={Target} />
                <PipelineStat label="Average risk (open alerts)" value={data.averageRisk.toFixed(1)} icon={Gauge} />
                <PipelineStat label="Avg. detection latency" value={`${data.detectionLatencyMs.toFixed(2)} ms/event`} icon={Timer} />
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}