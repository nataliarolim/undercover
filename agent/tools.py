"""Every tool the UnderCover Agent has, and the claim agent behind work_claim."""

import json
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

from langchain.tools import ToolRuntime, tool
from langchain_core.language_models import BaseChatModel

from agent import api, harness

CLAIM_STEP_LIMIT = 50


@dataclass(frozen=True)
class RunContext:
    run_id: int
    model: BaseChatModel


@dataclass(frozen=True)
class ClaimContext:
    claim_id: str


class Todo(TypedDict):
    content: str
    status: Literal["to_do", "in_progress", "done", "left_for_handler"]


@tool
def get_queue(runtime: ToolRuntime[RunContext]) -> str:
    """List the waiting claims this run can still take."""
    return json.dumps(api.get_queue(runtime.context.run_id))


@tool
def write_todos(todos: list[Todo], runtime: ToolRuntime[RunContext]) -> str:
    """Replace your to-do list, which the team watches on the dashboard. Each item's
    status is to_do, in_progress, done or left_for_handler."""
    api.update_todos(runtime.context.run_id, todos)
    return "The to-do list is saved."


@tool
def work_claim(claim_id: str, runtime: ToolRuntime[RunContext]) -> str:
    """Hand one claim to a claims handler who starts fresh. Returns one line: the
    decision and payout, or what went wrong."""
    return work(runtime.context.run_id, claim_id, runtime.context.model)


QUEUE_TOOLS = [get_queue, write_todos, work_claim]


@tool
def get_claim(runtime: ToolRuntime[ClaimContext]) -> str:
    """Read the claim: the story, the items claimed and the documents."""
    return json.dumps(api.get_claim(runtime.context.claim_id))


@tool
def get_policy(policy_id: str) -> str:
    """Look up a policy: the plan, the add-ons, the trip and the travelers."""
    return json.dumps(api.get_policy(policy_id))


@tool
def get_claim_history(customer_id: str) -> str:
    """Look up the customer's earlier claims."""
    return json.dumps(api.get_claim_history(customer_id))


@tool
def list_sections() -> str:
    """List the sections of the wording and the manual, with the topics in each."""
    return json.dumps(api.list_sections())


@tool
def read_section(
    document: Literal["policy_wording", "claims_manual"], section: int
) -> str:
    """Read one section of the policy wording or the claims manual, by its number."""
    return json.dumps(api.read_section(document, section))


@tool
def record_decision(
    decision: Literal["approve", "decline", "refer"],
    payout: float,
    rationale: str,
    policy_section: str,
    runtime: ToolRuntime[ClaimContext],
) -> str:
    """Record the decision on the claim.

    payout: the amount to pay in US dollars, or 0 for a decline or a referral.
    rationale: two or three sentences that explain the decision.
    policy_section: the section of the wording that decides it,
    such as "Section 3, Trip Delay".
    """
    body = {
        "decision": decision,
        "payout": payout,
        "rationale": rationale,
        "policy_section": policy_section,
    }
    return json.dumps(api.record_decision(runtime.context.claim_id, body))


@tool
def pay_claim(amount: float, runtime: ToolRuntime[ClaimContext]) -> str:
    """Pay the claim its approved payout, in US dollars."""
    return json.dumps(api.pay_claim(runtime.context.claim_id, amount))


CLAIM_TOOLS = [
    get_claim,
    get_policy,
    get_claim_history,
    list_sections,
    read_section,
    record_decision,
    pay_claim,
]
REFUSALS = harness.refusals(api.Refused)


def outcome(claim: dict[str, Any]) -> str:
    """Describe where a claim stands after its claim agent, in one line."""
    claim_id, status = claim["claim_id"], claim["status"]
    if status == "waiting":
        return (
            f"{claim_id} failed: {claim['error']}. "
            f"Back in the queue after attempt {claim['attempts']}"
        )
    if status == "left_for_handler":
        return (
            f"{claim_id} failed: {claim['error']}. "
            f"Left for a handler after {claim['attempts']} attempts"
        )
    if claim["decision"] != "approve":
        return f"{claim_id} {claim['decision']}"
    if status == "waiting_for_sign_off":
        payment = "waiting for sign-off"
    else:
        payment = "not paid" if claim["paid_amount"] is None else "paid"
    return f"{claim_id} approve ${claim['payout']:,.2f}, {payment}"


def work(run_id: int, claim_id: str, llm: BaseChatModel) -> str:
    """Have a fresh claim agent decide a claim, and describe the outcome in a line.

    However the claim agent ends, a claim it left in progress is released.
    """
    attempt = api.start_claim(claim_id, run_id)["attempts"]
    instructions = api.get_instructions()["claim"]
    agent = harness.create(llm, CLAIM_TOOLS, instructions, ClaimContext, [REFUSALS])
    error = "The agent finished without a decision"
    try:
        harness.run(
            agent,
            f"Decide claim {claim_id}.",
            ClaimContext(claim_id),
            harness.config(f"{run_id}-{claim_id}-{attempt}", CLAIM_STEP_LIMIT),
            lambda step: api.add_step(claim_id, step),
        )
    except Exception as failure:
        # One claim's failure, whatever it is, must never stop the run.
        error = f"{type(failure).__name__}: {failure}"[:300]
    claim = api.get_claim(claim_id)
    if claim["status"] == "in_progress":
        claim = api.release_claim(claim_id, error)
    return outcome(claim)
