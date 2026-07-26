import { lazy } from "react";
import { createBrowserRouter } from "react-router-dom";

import { App } from "@/App";

const DashboardPage = lazy(() => import("@/pages/DashboardPage"));
const AlertsPage = lazy(() => import("@/pages/AlertsPage"));
const EntitiesPage = lazy(() => import("@/pages/EntitiesPage"));
const AnalyticsPage = lazy(() => import("@/pages/AnalyticsPage"));
const SystemHealthPage = lazy(() => import("@/pages/SystemHealthPage"));
const SettingsPage = lazy(() => import("@/pages/SettingsPage"));
const NotFoundPage = lazy(() => import("@/pages/NotFoundPage"));

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "alerts", element: <AlertsPage /> },
      { path: "entities", element: <EntitiesPage /> },
      { path: "analytics", element: <AnalyticsPage /> },
      { path: "system-health", element: <SystemHealthPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);