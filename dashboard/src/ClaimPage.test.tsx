import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Claim, Step } from "./api";
import { ClaimPage } from "./ClaimPage";
import { CLAIM, HANDLERS, HISTORY, POLICY, stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const HELD: Claim = {
  ...CLAIM,
  status: "waiting_for_sign_off",
  decision: "approve",
  payout: 3750,
  rationale: "The fall is a sudden injury during the trip.",
  policy_section: "Section 7, Emergency Medical",
};

function stubClaim(claim: Claim | (() => Claim), steps: Step[] = []) {
  return stubApi({
    "/api/claims/CLM-1001": claim,
    "/api/claims/CLM-1001/steps": steps,
    "/api/policies/POL-2001": POLICY,
    "/api/customers/CUS-3001/history": HISTORY,
    "/api/handlers": HANDLERS,
  });
}

function panel(name: string) {
  return within(screen.getByRole("region", { name }));
}

it("shows the claim in full, as the agent reads it", async () => {
  stubClaim(CLAIM);
  render(<ClaimPage claimId="CLM-1001" />);

  expect(
    await screen.findByText("My flight home from Rome was canceled."),
  ).toBeDefined();
  expect(screen.getByText("Waiting")).toBeDefined();
  expect(panel("Items claimed").getAllByRole("row")).toHaveLength(3);
  expect(panel("Items claimed").getByText("$245.00")).toBeDefined();
  expect(panel("Documents").getByText("Hotel receipt")).toBeDefined();
  expect(panel("Decision").getByText("No decision yet.")).toBeDefined();
  expect(panel("Agent steps").getByText("No steps yet.")).toBeDefined();
  expect(
    panel("What the agent read").getByText("No sections read yet."),
  ).toBeDefined();

  expect(await screen.findByText("Premium")).toBeDefined();
  expect(
    panel("Policy").getByText("Rome, Italy, Jun 10, 2026 to Jun 18, 2026"),
  ).toBeDefined();
  expect(panel("Policy").getByText("None")).toBeDefined();
  expect(
    await screen.findByText("Maya Patel", { selector: "h2" }),
  ).toBeDefined();
  expect(panel("Claim history").getByText("CLM-0412")).toBeDefined();
});

it("shows the agent's steps while it works", async () => {
  stubClaim({ ...CLAIM, status: "in_progress" }, [
    { step_id: 1, kind: "tool_call", name: "get_claim", content: "{}" },
    {
      step_id: 2,
      kind: "tool_result",
      name: "get_claim",
      content: '{"claim_id":"CLM-1001"}',
    },
    {
      step_id: 3,
      kind: "tool_call",
      name: "pay_claim",
      content: '{"amount": 3750}',
    },
    {
      step_id: 4,
      kind: "tool_result",
      name: "pay_claim",
      content: '{"detail":"Payouts over $1,000.00 need a handler\'s sign-off"}',
    },
    {
      step_id: 5,
      kind: "message",
      name: "agent",
      content: "Approved; it waits for sign-off.",
    },
  ]);
  render(<ClaimPage claimId="CLM-1001" />);

  const steps = within(await screen.findByRole("list", { name: "" }));
  expect(
    await screen.findByText("The agent is working on this claim."),
  ).toBeDefined();
  expect(steps.getAllByRole("listitem")).toHaveLength(5);
  expect(screen.getByText('{"claim_id":"CLM-1001"}')).toBeDefined();
  expect(screen.getByText("Refused")).toBeDefined();
  expect(
    screen.getByText("Payouts over $1,000.00 need a handler's sign-off"),
  ).toBeDefined();
  expect(screen.getByText("Approved; it waits for sign-off.")).toBeDefined();
});

it("lists the sections the agent read, once each", async () => {
  const section = JSON.stringify({
    document: "claims_manual",
    section: 7,
    title: "Interpretation notes",
    topics: ["Wild animals"],
    text: "These notes record how UnderCover reads the wording.",
  });
  const read = (step_id: number, content: string): Step => ({
    step_id,
    kind: "tool_result",
    name: "read_section",
    content,
  });
  stubClaim({ ...CLAIM, status: "in_progress" }, [
    read(1, section),
    read(2, section),
    read(3, '{"detail":"There is no section 99 in policy_wording"}'),
  ]);
  render(<ClaimPage claimId="CLM-1001" />);

  expect(
    await screen.findByText("Claims manual, 7. Interpretation notes"),
  ).toBeDefined();
  expect(panel("What the agent read").getAllByRole("listitem")).toHaveLength(1);
});

it("shows a claim left for a handler with its error", async () => {
  stubClaim(
    {
      ...CLAIM,
      status: "left_for_handler",
      attempts: 2,
      error: "TimeoutError: The model took too long",
    },
    [
      {
        step_id: 1,
        kind: "error",
        name: "Attempt 2 of 2",
        content: "TimeoutError: The model took too long",
      },
    ],
  );
  render(<ClaimPage claimId="CLM-1001" />);

  expect(
    await screen.findByText(
      "TimeoutError: The model took too long. Left for a handler after 2 attempts.",
    ),
  ).toBeDefined();
  expect(
    panel("Agent steps").getByText(
      "Attempt 2 of 2: TimeoutError: The model took too long",
    ),
  ).toBeDefined();
  expect(screen.getAllByText("Failed")).toHaveLength(2);
});

it("shows a claim back in the queue after a failure", async () => {
  stubClaim({
    ...CLAIM,
    attempts: 1,
    error: "The agent finished without a decision",
  });
  render(<ClaimPage claimId="CLM-1001" />);
  expect(
    await screen.findByText(
      "The agent finished without a decision. Back in the queue after attempt 1.",
    ),
  ).toBeDefined();
});

it("signs off an approval over the limit, which pays it", async () => {
  let signedOff = false;
  const fetchMock = stubApi({
    "/api/claims/CLM-1001": () =>
      signedOff
        ? {
            ...HELD,
            status: "decided",
            paid_amount: 3750,
            signed_off_by: "HND-01",
          }
        : HELD,
    "/api/claims/CLM-1001/steps": [],
    "/api/policies/POL-2001": POLICY,
    "/api/customers/CUS-3001/history": HISTORY,
    "/api/handlers": HANDLERS,
    "POST /api/claims/CLM-1001/sign-off": () => {
      signedOff = true;
      return {};
    },
  });
  render(<ClaimPage claimId="CLM-1001" />);

  const button = await screen.findByRole("button", {
    name: "Sign off and pay $3,750.00",
  });
  expect(button.hasAttribute("disabled")).toBe(true);
  await screen.findByRole("option", { name: "Dana Whitfield" });
  fireEvent.change(screen.getByLabelText("Handler"), {
    target: { value: "HND-01" },
  });
  fireEvent.click(button);

  expect(await screen.findByText("Decided")).toBeDefined();
  expect(screen.getByText(/signed off by Dana Whitfield/)).toBeDefined();
  expect(
    screen.getByText("$3,750.00", { selector: ".mono:not(.payout)" }),
  ).toBeDefined();
  const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
  expect(post?.[1]?.body).toBe('{"handler_id":"HND-01"}');
});

it("shows why a sign-off failed", async () => {
  stubClaim(HELD);
  render(<ClaimPage claimId="CLM-1001" />);

  await screen.findByRole("option", { name: "Dana Whitfield" });
  fireEvent.change(screen.getByLabelText("Handler"), {
    target: { value: "HND-01" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Sign off and pay $3,750.00" }),
  );
  expect((await screen.findByRole("alert")).textContent).toBe(
    "There is no POST /api/claims/CLM-1001/sign-off",
  );
});

it("shows a paid approval within the limit", async () => {
  stubClaim({ ...HELD, status: "decided", payout: 420, paid_amount: 420 });
  render(<ClaimPage claimId="CLM-1001" />);
  expect(await screen.findByText("Paid")).toBeDefined();
  expect(screen.queryByText(/signed off by/)).toBeNull();
});

it("shows an approval the agent did not pay", async () => {
  stubClaim({ ...HELD, status: "decided", payout: 420 });
  render(<ClaimPage claimId="CLM-1001" />);
  expect(await screen.findByText("Not paid")).toBeDefined();
});

it("shows a decline with its reasons and no payment", async () => {
  stubClaim({
    ...CLAIM,
    status: "decided",
    decision: "decline",
    payout: 0,
    rationale: "The bag was left unattended.",
    policy_section: "Section 5, Baggage and Personal Effects",
  });
  render(<ClaimPage claimId="CLM-1001" />);
  expect(await screen.findByText("Decline")).toBeDefined();
  expect(screen.getByText("The bag was left unattended.")).toBeDefined();
  expect(
    screen.getByText("Section 5, Baggage and Personal Effects"),
  ).toBeDefined();
  expect(screen.queryByText(/Paid|Not paid/)).toBeNull();
});

it("says when there is no such claim", async () => {
  stubApi({});
  render(<ClaimPage claimId="CLM-0000" />);
  expect((await screen.findByRole("alert")).textContent).toBe(
    "There is no /api/claims/CLM-0000",
  );
});
