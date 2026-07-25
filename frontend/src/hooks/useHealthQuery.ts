import { useQuery } from "@tanstack/react-query";
import type { UseQueryResult } from "@tanstack/react-query";

import type { ApiError } from "@/services/api";
import { getHealth } from "@/services/health.service";
import type { HealthCheckResponse } from "@/services/health.service";

const HEALTH_CHECK_INTERVAL_MS = 30_000;

export function useHealthQuery(): UseQueryResult<HealthCheckResponse, ApiError> {
  return useQuery<HealthCheckResponse, ApiError>({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: HEALTH_CHECK_INTERVAL_MS,
    // No retry: a scheduled retry can be left "paused" indefinitely by
    // TanStack Query's online-detection (neither loading, errored, nor
    // showing data — a stuck UI). A status card doesn't need aggressive
    // immediate retries anyway; refetchInterval already re-checks every
    // 30s, which is a perfectly adequate retry cadence for a health probe.
    retry: false,
  });
}