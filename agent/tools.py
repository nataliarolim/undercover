"""Every tool the UnderCover Agent has, and the claim agent that uses them."""

import json
from dataclasses import dataclass
from typing import Literal

from langchain.tools import ToolRuntime, tool
from langchain_core.language_models import BaseChatModel

from agent import api, harness


@dataclass(frozen=True)
class ClaimContext:
    claim_id: str


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


def run_claim(claim_id: str, run_id: int, thread_id: str, llm: BaseChatModel) -> str:
    """Start a claim and have a claim agent decide it, posting each step."""
    api.start_claim(claim_id, run_id)
    instructions = api.get_instructions()["claim"]
    agent = harness.create(llm, CLAIM_TOOLS, instructions, ClaimContext, [REFUSALS])
    return harness.run(
        agent,
        f"Decide claim {claim_id}.",
        ClaimContext(claim_id),
        thread_id,
        lambda step: api.add_step(claim_id, step),
    )
