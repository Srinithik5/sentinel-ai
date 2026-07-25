export const ROUTES = {
  dashboard: "/",
  alerts: "/alerts",
  entities: "/entities",
  analytics: "/analytics",
  settings: "/settings",
} as const;

export type AppRoute = (typeof ROUTES)[keyof typeof ROUTES];