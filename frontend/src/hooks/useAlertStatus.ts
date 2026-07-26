import { useCallback, useSyncExternalStore } from "react";

import type { AlertStatus } from "@/types/dashboard";

/**
 * Client-side triage status for alerts. The pipeline itself has no
 * ticketing/workflow system — every exported alert is genuinely untouched
 * ("open") until an analyst acts on it in this UI. Status changes made
 * here are real interactive state (persisted to localStorage so a reload
 * doesn't lose triage progress), never fabricated historical data.
 */

const STORAGE_KEY = "sentinelai.alertStatus.v1";
const listeners = new Set<() => void>();

function readStore(): Record<string, AlertStatus> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Record<string, AlertStatus>) : {};
  } catch {
    return {};
  }
}

let cache = readStore();

function writeStore(next: Record<string, AlertStatus>): void {
  cache = next;
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot(): Record<string, AlertStatus> {
  return cache;
}

export function useAlertStatusMap(): Record<string, AlertStatus> {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

export function useAlertStatus(eventId: string): {
  status: AlertStatus;
  setStatus: (status: AlertStatus) => void;
} {
  const statusMap = useAlertStatusMap();
  const status = statusMap[eventId] ?? "open";

  const setStatus = useCallback(
    (next: AlertStatus) => {
      writeStore({ ...readStore(), [eventId]: next });
    },
    [eventId],
  );

  return { status, setStatus };
}

export const ALERT_STATUS_LABELS: Record<AlertStatus, string> = {
  open: "Open",
  investigating: "Investigating",
  resolved: "Resolved",
  false_positive: "False Positive",
};