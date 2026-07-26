import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 py-16 text-center">
      <Icon className="h-8 w-8 text-slate-300" aria-hidden="true" />
      <div className="space-y-1">
        <p className="text-sm font-medium text-primary">{title}</p>
        {description ? <p className="max-w-sm text-sm text-slate-500">{description}</p> : null}
      </div>
      {action}
    </div>
  );
}

export interface ErrorStateProps {
  title?: string;
  message: string;
}

export function ErrorState({ title = "Something went wrong", message }: ErrorStateProps) {
  return (
    <div role="alert" className="flex flex-col items-center gap-2 py-16 text-center">
      <p className="text-sm font-medium text-primary">{title}</p>
      <p className="max-w-sm text-sm text-slate-500">{message}</p>
    </div>
  );
}