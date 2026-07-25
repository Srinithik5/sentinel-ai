import axios, { AxiosError } from "axios";
import type { InternalAxiosRequestConfig } from "axios";

import { getAuthToken } from "@/lib/authToken";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
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