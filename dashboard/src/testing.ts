import { vi } from "vitest";
import type { ClaimSummary } from "./api";

/** Stub fetch with replies keyed by path, such as "/api/claims" or "POST /api/claims/CLM-1001/sign-off". */
export function stubApi(replies: Record<string, unknown>) {
  const fetchMock = vi.fn((path: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    const key = method === "GET" ? path : `${method} ${path}`;
    const reply =
      key in replies
        ? Response.json(replies[key])
        : Response.json({ detail: `There is no ${key}` }, { status: 404 });
    return Promise.resolve(reply);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export const WAITING: ClaimSummary = {
  claim_id: "CLM-1001",
  summary: "Flight home canceled by the airline",
  claim_type: "trip_delay",
  amount_claimed: 420,
  status: "waiting",
  decision: null,
  payout: null,
};

export const HELD: ClaimSummary = {
  claim_id: "CLM-1003",
  summary: "Hospital visit abroad after a fall",
  claim_type: "emergency_medical",
  amount_claimed: 3800,
  status: "waiting_for_sign_off",
  decision: "approve",
  payout: 3750,
};
