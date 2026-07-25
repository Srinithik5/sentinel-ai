import { ShieldCheck } from "lucide-react";
import { NavLink } from "react-router-dom";

import { NAV_ITEMS } from "@/config/navigation";
import { cn } from "@/lib/utils";

export function Sidebar() {
  return (
    <aside className="flex w-64 flex-shrink-0 flex-col bg-primary text-white">
      <div className="flex h-16 items-center gap-2 border-b border-white/10 px-6">
        <ShieldCheck className="h-6 w-6 text-accent" aria-hidden="true" />
        <span className="text-base font-semibold tracking-tight">SentinelAI</span>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4" aria-label="Primary">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-white/10 text-white"
                  : "text-white/70 hover:bg-white/5 hover:text-white",
              )
            }
          >
            {({ isActive }) => (
              <>
                <item.icon
                  className={cn("h-4 w-4", isActive ? "text-accent" : "text-white/50")}
                  aria-hidden="true"
                />
                {item.label}
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}