export const ROUTES = {
  dashboard: "/",
  alerts: "/alerts",
  entities: "/entities",
  analytics: "/analytics",
  systemHealth: "/system-health",
  settings: "/settings",
} as const;

export type AppRoute = (typeof ROUTES)[keyof typeof ROUTES];