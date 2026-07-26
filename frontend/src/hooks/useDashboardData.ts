import { useQuery } from "@tanstack/react-query";
import type { UseQueryResult } from "@tanstack/react-query";

import {
  getAlerts,
  getAnalytics,
  getMitreRegistry,
  getOverviewMetrics,
  getSystemHealth,
} from "@/services/dashboard.service";
import type { Alert, AnalyticsData, MitreEntry, OverviewMetrics, SystemHealthData } from "@/types/dashboard";

// The underlying fixtures are static exports of a verified pipeline run
// rather than a live feed, so a longer staleTime avoids redundant
// re-fetching while still allowing an explicit refetch (e.g. a "Refresh"
// action) to pick up a newer export.
const STALE_TIME_MS = 5 * 60_000;

export function useOverviewMetrics(): UseQueryResult<OverviewMetrics, Error> {
  return useQuery({
    queryKey: ["dashboard", "overview"],
    queryFn: getOverviewMetrics,
    staleTime: STALE_TIME_MS,
  });
}

export function useAlerts(): UseQueryResult<Alert[], Error> {
  return useQuery({
    queryKey: ["dashboard", "alerts"],
    queryFn: getAlerts,
    staleTime: STALE_TIME_MS,
  });
}

export function useAnalytics(): UseQueryResult<AnalyticsData, Error> {
  return useQuery({
    queryKey: ["dashboard", "analytics"],
    queryFn: getAnalytics,
    staleTime: STALE_TIME_MS,
  });
}

export function useMitreRegistry(): UseQueryResult<MitreEntry[], Error> {
  return useQuery({
    queryKey: ["dashboard", "mitre"],
    queryFn: getMitreRegistry,
    staleTime: STALE_TIME_MS,
  });
}

export function useSystemHealth(): UseQueryResult<SystemHealthData, Error> {
  return useQuery({
    queryKey: ["dashboard", "system-health"],
    queryFn: getSystemHealth,
    staleTime: STALE_TIME_MS,
  });
}