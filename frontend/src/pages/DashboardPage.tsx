import { LayoutDashboard } from "lucide-react";

import { Card, CardContent } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";

export default function DashboardPage() {
  return (
    <>
      <PageHeader
        title="Dashboard"
        description="A consolidated view of behavioral anomaly signals across your environment."
      />
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
          <LayoutDashboard className="h-8 w-8 text-slate-300" aria-hidden="true" />
          <p className="text-sm text-slate-500">
            Dashboard widgets will appear here once detection and analytics are enabled in a
            later phase.
          </p>
        </CardContent>
      </Card>
    </>
  );
}