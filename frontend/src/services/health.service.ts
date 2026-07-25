import { apiClient } from "@/services/api";

export interface HealthCheckResponse {
  status: string;
  service: string;
  version: string;
  database: string;
  timestamp?: string;
}

export async function getHealth(): Promise<HealthCheckResponse> {
  // The backend intentionally returns 503 (not 200) for a "degraded" health
  // state while still sending a fully-formed body — validateStatus treats
  // that as a valid response so the UI can render the real degraded state
  // instead of falling into the generic "unavailable" error branch.
  const response = await apiClient.get<HealthCheckResponse>("/health", {
    validateStatus: (status) => status === 200 || status === 503,
  });
  return response.data;
}