import { forwardRef } from "react";
import type { InputHTMLAttributes } from "react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  leadingIcon?: LucideIcon;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, leadingIcon: LeadingIcon, ...props }, ref) => {
    return (
      <div className="relative flex items-center">
        {LeadingIcon ? (
          <LeadingIcon
            className="pointer-events-none absolute left-3 h-4 w-4 text-slate-400"
            aria-hidden="true"
          />
        ) : null}
        <input
          ref={ref}
          className={cn(
            "h-9 w-full rounded-md border border-slate-300 bg-white text-sm text-primary placeholder:text-slate-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50",
            LeadingIcon ? "pl-9 pr-3" : "px-3",
            className,
          )}
          {...props}
        />
      </div>
    );
  },
);

Input.displayName = "Input";