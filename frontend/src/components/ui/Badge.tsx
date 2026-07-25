import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const BADGE_VARIANTS = {
  neutral: "bg-slate-100 text-slate-600",
  accent: "bg-accent/10 text-accent",
  success: "bg-emerald-100 text-emerald-700",
  warning: "bg-amber-100 text-amber-700",
  danger: "bg-red-100 text-red-700",
} as const;

export type BadgeVariant = keyof typeof BADGE_VARIANTS;

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

export function Badge({ className, variant = "neutral", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize",
        BADGE_VARIANTS[variant],
        className,
      )}
      {...props}
    />
  );
}