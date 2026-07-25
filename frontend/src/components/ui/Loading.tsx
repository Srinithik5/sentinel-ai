import { Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

export interface LoadingProps {
  label?: string;
  fullScreen?: boolean;
  className?: string;
}

export function Loading({ label = "Loading", fullScreen = false, className }: LoadingProps) {
  return (
    <div
      role="status"
      className={cn(
        "flex flex-col items-center justify-center gap-3 text-slate-500",
        fullScreen ? "h-screen w-full bg-background" : "py-16",
        className,
      )}
    >
      <Loader2 className="h-6 w-6 animate-spin text-accent" aria-hidden="true" />
      <span className="text-sm">{label}</span>
    </div>
  );
}