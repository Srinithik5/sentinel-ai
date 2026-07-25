import type { LucideIcon } from "lucide-react";
import { BarChart3, Boxes, LayoutDashboard, Settings, ShieldAlert } from "lucide-react";

import { ROUTES } from "@/routes/paths";

export interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", path: ROUTES.dashboard, icon: LayoutDashboard },
  { label: "Alerts", path: ROUTES.alerts, icon: ShieldAlert },
  { label: "Entities", path: ROUTES.entities, icon: Boxes },
  { label: "Analytics", path: ROUTES.analytics, icon: BarChart3 },
  { label: "Settings", path: ROUTES.settings, icon: Settings },
];