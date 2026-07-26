import { useState } from "react";

import { AlertDetailsPanel } from "@/components/dashboard/AlertDetailsPanel";
import { AlertQueue } from "@/components/dashboard/AlertQueue";
import { PageHeader } from "@/components/ui/PageHeader";
import type { Alert } from "@/types/dashboard";

export default function AlertsPage() {
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  return (
    <>
      <PageHeader
        title="Live Alert Queue"
        description="Anomalous events flagged by the Phase 4 Detection Engine and classified by Phase 5, ready for analyst triage."
      />
      <AlertQueue onSelectAlert={setSelectedAlert} />
      <AlertDetailsPanel alert={selectedAlert} onClose={() => setSelectedAlert(null)} />
    </>
  );
}