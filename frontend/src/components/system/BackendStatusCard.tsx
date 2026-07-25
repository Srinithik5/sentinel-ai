import { XCircle } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import type { BadgeVariant } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Loading } from "@/components/ui/Loading";
import { useHealthQuery } from "@/hooks/useHealthQuery";

interface StatusRowProps {
  label: string;
  value: string;
  tone?: BadgeVariant;
}

function StatusRow({ label, value, tone }: StatusRowProps) {
  return (
    <div className="flex items-center justify-between border-b border-slate-100 py-2.5 last:border-b-0">
      <span className="text-sm text-slate-500">{label}</span>
      {tone ? (
        <Badge variant={tone}>{value}</Badge>
      ) : (
        <span className="text-sm font-medium text-primary">{value}</span>
      )}
    </div>
  );
}

export function BackendStatusCard() {
  const { data, error, isLoading, isError } = useHealthQuery();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Backend Status</CardTitle>
      </CardHeader>
      <CardContent aria-live="polite">
        {isLoading ? (
          <Loading label="Checking backend..." />
        ) : isError ? (
          <div role="alert" className="flex flex-col items-center gap-3 py-6 text-center">
            <XCircle className="h-8 w-8 text-red-400" aria-hidden="true" />
            <div className="space-y-1">
              <p className="text-sm font-medium text-primary">Backend unavailable</p>
              <p className="text-sm text-slate-500">{error.message}</p>
            </div>
          </div>
        ) : data ? (
          <div>
            <StatusRow
              label="Backend"
              value={data.status === "healthy" ? "Healthy" : "Degraded"}
              tone={data.status === "healthy" ? "success" : "warning"}
            />
            <StatusRow
              label="Database"
              value={data.database === "connected" ? "Connected" : "Disconnected"}
              tone={data.database === "connected" ? "success" : "danger"}
            />
            <StatusRow label="API Version" value={data.version} />
            <StatusRow label="Backend Timestamp" value={data.timestamp ?? "Not reported"} />
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}