import { Crosshair, ExternalLink, ShieldAlert, Tags } from "lucide-react";

import { SeverityBadge } from "@/components/dashboard/SeverityBadge";
import { Skeleton } from "@/components/ui/Skeleton";
import { useMitreRegistry } from "@/hooks/useDashboardData";
import type { Alert } from "@/types/dashboard";

export function MitrePanel({ alert }: { alert: Alert }) {
  const { data: registry, isLoading } = useMitreRegistry();
  const entry = registry?.find((item) => item.attackType === alert.attackType);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="rounded-md border border-slate-200 p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-accent" aria-hidden="true" />
            <h3 className="text-base font-semibold text-primary">{alert.attackDisplayName}</h3>
          </div>
          <SeverityBadge severity={entry?.severity ?? alert.severity} />
        </div>

        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <dt className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-slate-400">
              <Tags className="h-3.5 w-3.5" aria-hidden="true" />
              Tactic
            </dt>
            <dd className="mt-1 text-sm font-medium text-primary">{alert.mitreTactic}</dd>
          </div>
          <div>
            <dt className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-slate-400">
              <Crosshair className="h-3.5 w-3.5" aria-hidden="true" />
              Technique
            </dt>
            <dd className="mt-1 text-sm font-medium text-primary">{alert.mitreTechnique}</dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="mitre-description-heading">
        <h3 id="mitre-description-heading" className="mb-2 text-sm font-semibold text-primary">
          Description
        </h3>
        <p className="rounded-md bg-slate-50 p-4 text-sm leading-relaxed text-slate-600">
          {entry?.description ?? "No registry description available for this attack type."}
        </p>
      </section>

      {alert.mitreTechnique.startsWith("T") ? (
        <a
          href={`https://attack.mitre.org/techniques/${alert.mitreTechnique.split(" ")[0].replace(".", "/")}/`}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          View on MITRE ATT&amp;CK
          <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
        </a>
      ) : (
        <p className="text-sm text-slate-400">No MITRE technique is mapped for an unclassified attack type.</p>
      )}
    </div>
  );
}