import { useEffect, useState } from "react";

export const STATUSES = [
  "waiting",
  "in_progress",
  "waiting_for_sign_off",
  "decided",
  "left_for_handler",
] as const;
export type Status = (typeof STATUSES)[number];
export type DecisionKind = "approve" | "decline" | "refer";

export interface ClaimSummary {
  claim_id: string;
  summary: string;
  claim_type: string;
  amount_claimed: number;
  status: Status;
  decision: DecisionKind | null;
  payout: number | null;
}

export interface Item {
  description: string;
  category: string;
  amount: number;
}

export interface ClaimDocument {
  name: string;
  type: string;
  content: string;
}

export interface Claim extends ClaimSummary {
  policy_id: string;
  customer_id: string;
  submitted_on: string;
  incident_date: string;
  incident_location: string;
  story: string;
  items: Item[];
  documents: ClaimDocument[];
  rationale: string | null;
  policy_section: string | null;
  paid_amount: number | null;
  signed_off_by: string | null;
}

export interface Policy {
  policy_id: string;
  plan: string;
  add_ons: string[];
  purchased_on: string;
  trip: {
    destination: string;
    departs_on: string;
    returns_on: string;
    trip_cost: number;
  };
  travelers: string[];
}

export interface PreviousClaim {
  claim_id: string;
  filed_on: string;
  claim_type: string;
  summary: string;
  outcome: string;
  amount_paid: number;
}

export interface ClaimHistory {
  customer_id: string;
  name: string;
  customer_since: string;
  previous_claims: PreviousClaim[];
}

export interface Handler {
  handler_id: string;
  name: string;
  role: string;
}

export interface Step {
  step_id: number;
  kind: "tool_call" | "tool_result" | "message" | "error";
  name: string;
  content: string;
}

export interface Instructions {
  claim: string;
}

export type DocumentName = "policy_wording" | "claims_manual";

export interface SectionRead {
  document: DocumentName;
  section: number;
  title: string;
}

export const POLL_MS = 2000;

const API = "/api";

/** Every path the dashboard calls on the backend. */
export const paths = {
  claims: `${API}/claims`,
  claim: (claimId: string) => `${API}/claims/${claimId}`,
  steps: (claimId: string) => `${API}/claims/${claimId}/steps`,
  signOff: (claimId: string) => `${API}/claims/${claimId}/sign-off`,
  policy: (policyId: string) => `${API}/policies/${policyId}`,
  history: (customerId: string) => `${API}/customers/${customerId}/history`,
  handlers: `${API}/handlers`,
  instructions: `${API}/instructions`,
};

async function read<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const { detail } = (await response.json()) as { detail: string };
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export async function getJson<T>(path: string): Promise<T> {
  return read<T>(await fetch(path));
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return read<T>(response);
}

export interface Loaded<T> {
  data?: T;
  error?: string;
}

/** Fetch a path from the API, and fetch it again every POLL_MS if asked. */
export function useApi<T>(
  path: string,
  poll = false,
): Loaded<T> & { reload: () => void } {
  const [loaded, setLoaded] = useState<Loaded<T>>({});
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    const load = () => {
      getJson<T>(path).then(
        (data) => {
          if (active) setLoaded({ data });
        },
        (error: unknown) => {
          if (active) setLoaded({ error: (error as Error).message });
        },
      );
    };
    load();
    const timer = poll ? setInterval(load, POLL_MS) : undefined;
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [path, poll, version]);

  return {
    ...loaded,
    reload: () => {
      setVersion((current) => current + 1);
    },
  };
}
