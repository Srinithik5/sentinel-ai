import { Settings as SettingsIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";

export default function SettingsPage() {
  return (
    <>
      <PageHeader
        title="Settings"
        description="Platform, detection, and notification configuration."
      />
      <Card>
        <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
          <SettingsIcon className="h-8 w-8 text-slate-300" aria-hidden="true" />
          <p className="text-sm text-slate-500">
            Configuration options will be available here in a later phase.
          </p>
        </CardContent>
      </Card>
    </>
  );
}