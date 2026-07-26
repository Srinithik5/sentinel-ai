import axios, { AxiosError } from "axios";
import type { InternalAxiosRequestConfig } from "axios";

import { getAuthToken } from "@/lib/authToken";

// Render's fromService gives just the domain (e.g. https://sentinel-ai-backend.onrender.com).
// Locally, .env includes the full path. This ensures /api/v1 is always present.
function resolveBaseUrl(): string {
  const raw = import.meta.env.VITE_API_BASE_URL ?? "";
  return raw.includes("/api/v1") ? raw : `${raw.replace(/\/+$/, "")}/api/v1`;
}

export const apiClient = axios.create({
  baseURL: resolveBaseUrl(),
  timeout: 10_000,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAuthToken();
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

export interface ApiError {
  status: number | null;
  message: string;
}

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string }>) => {
    const apiError: ApiError = {
      status: error.response?.status ?? null,
      message: error.response?.data?.detail ?? error.message ?? "Unexpected network error",
    };
    return Promise.reject(apiError);
  },
);