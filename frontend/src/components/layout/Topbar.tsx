import { Bell, Search } from "lucide-react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

export function Topbar() {
  return (
    <header className="flex h-16 flex-shrink-0 items-center justify-between gap-4 border-b border-slate-200 bg-white px-6">
      <div className="w-full max-w-sm">
        <Input
          type="search"
          placeholder="Search entities, alerts, and analytics"
          leadingIcon={Search}
          aria-label="Search"
        />
      </div>

      <div className="flex flex-shrink-0 items-center gap-3">
        <Badge variant="neutral">{import.meta.env.MODE}</Badge>
        <Button variant="ghost" size="icon" aria-label="Notifications">
          <Bell className="h-5 w-5" aria-hidden="true" />
        </Button>
      </div>
    </header>
  );
}