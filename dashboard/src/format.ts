import type { DecisionKind, Status } from "./api";

const usd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

const days = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeZone: "UTC",
});

export function dollars(amount: number): string {
  return usd.format(amount);
}

/** Format a date such as 2026-06-18 as Jun 18, 2026. */
export function day(date: string): string {
  return days.format(new Date(`${date}T00:00:00Z`));
}

export const STATUS_LABELS: Record<Status, string> = {
  waiting: "Waiting",
  in_progress: "In progress",
  waiting_for_sign_off: "Waiting for sign-off",
  decided: "Decided",
};

export const DECISION_LABELS: Record<DecisionKind, string> = {
  approve: "Approve",
  decline: "Decline",
  refer: "Refer",
};

/** Turn an identifier such as trip_delay into a label such as Trip delay. */
export function label(identifier: string): string {
  const words = identifier.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}
