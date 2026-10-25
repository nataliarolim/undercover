import { vi } from "vitest";
import type {
  Claim,
  ClaimHistory,
  ClaimSummary,
  Handler,
  Policy,
  Run,
} from "./api";

/**
 * Stub fetch with replies keyed by path, such as "/api/claims" or
 * "POST /api/claims/CLM-1003/sign-off". A function reply runs on each call.
 */
export function stubApi(replies: Record<string, unknown>) {
  const fetchMock = vi.fn((path: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    const key = method === "GET" ? path : `${method} ${path}`;
    if (!(key in replies)) {
      const detail = `There is no ${key}`;
      return Promise.resolve(Response.json({ detail }, { status: 404 }));
    }
    const reply = replies[key];
    const body =
      typeof reply === "function" ? (reply as () => unknown)() : reply;
    return Promise.resolve(Response.json(body));
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
  attempts: 0,
};

export const HELD: ClaimSummary = {
  claim_id: "CLM-1003",
  summary: "Hospital visit abroad after a fall",
  claim_type: "emergency_medical",
  amount_claimed: 3800,
  status: "waiting_for_sign_off",
  decision: "approve",
  payout: 3750,
  attempts: 1,
};

export const CLAIM: Claim = {
  ...WAITING,
  policy_id: "POL-2001",
  customer_id: "CUS-3001",
  submitted_on: "2026-06-24",
  incident_date: "2026-06-18",
  incident_location: "Rome, Italy",
  story: "My flight home from Rome was canceled.",
  items: [
    {
      description: "Airport hotel, one night",
      category: "accommodation",
      amount: 245,
    },
    { description: "Dinner and breakfast", category: "meals", amount: 95 },
  ],
  documents: [
    {
      name: "Hotel receipt",
      type: "receipt",
      content: "Hotel Aurelia Fiumicino. Total paid: $245.00.",
    },
  ],
  rationale: null,
  policy_section: null,
  paid_amount: null,
  signed_off_by: null,
  error: null,
  run_id: null,
};

export const RUN: Run = {
  run_id: 3,
  cap: 5,
  status: "running",
  todos: [
    { content: "Decide CLM-1001", status: "done" },
    { content: "Decide CLM-1002", status: "in_progress" },
    { content: "Decide CLM-1003", status: "to_do" },
    { content: "Decide CLM-1004", status: "left_for_handler" },
  ],
  summary: null,
  started_at: "2026-10-25T12:00:00+00:00",
  finished_at: null,
};

export const POLICY: Policy = {
  policy_id: "POL-2001",
  plan: "premium",
  add_ons: [],
  purchased_on: "2026-04-22",
  trip: {
    destination: "Rome, Italy",
    departs_on: "2026-06-10",
    returns_on: "2026-06-18",
    trip_cost: 3100,
  },
  travelers: ["Maya Patel"],
};

export const HISTORY: ClaimHistory = {
  customer_id: "CUS-3001",
  name: "Maya Patel",
  customer_since: "2023-04-11",
  previous_claims: [
    {
      claim_id: "CLM-0412",
      filed_on: "2024-08-19",
      claim_type: "baggage_delay",
      summary: "Checked bag arrived 30 hours late in Lisbon",
      outcome: "approved",
      amount_paid: 140,
    },
  ],
};

export const HANDLERS: Handler[] = [
  {
    handler_id: "HND-01",
    name: "Dana Whitfield",
    role: "Senior Claims Handler",
  },
  { handler_id: "HND-02", name: "Marcus Oyelaran", role: "Claims Handler" },
];
