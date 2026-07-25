import { BarChart3 } from "lucide-react";

import { Card, CardContent } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";

export default function AnalyticsPage() {
  return (
    <>
      <PageHeader
        title="Analytics"
        description="Trends and behavioral patterns derived from monitored entities over time."
      />
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
          <BarChart3 className="h-8 w-8 text-slate-300" aria-hidden="true" />
          <p className="text-sm text-slate-500">
            Analytics visualizations will appear here once behavioral models are trained.
          </p>
        </CardContent>
      </Card>
    </>
  );
}