"""The UnderCover Agent."""

import json
import os
from collections.abc import Iterator
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import BaseTool, tool
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv(override=True)

BACKEND_URL = "http://localhost:8000"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"


def backend() -> httpx.Client:
    """Return a client for the UnderCover backend."""
    return httpx.Client(base_url=BACKEND_URL, timeout=10)


def call(method: str, path: str, body: dict[str, Any] | None = None) -> str:
    """Call the backend for a tool, returning a refusal as text for the agent."""
    with backend() as client:
        response = client.request(method, path, json=body)
    if response.is_server_error:
        response.raise_for_status()
    return response.text


def make_tools(claim_id: str) -> list[BaseTool]:
    """Make the agent's tools, bound to the one claim it decides."""

    @tool
    def get_claim() -> str:
        """Read the claim: the story, the items claimed and the documents."""
        return call("GET", f"/api/claims/{claim_id}")

    @tool
    def get_policy(policy_id: str) -> str:
        """Look up a policy: the plan, the add-ons, the trip and the travelers."""
        return call("GET", f"/api/policies/{policy_id}")

    @tool
    def get_claim_history(customer_id: str) -> str:
        """Look up the customer's earlier claims."""
        return call("GET", f"/api/customers/{customer_id}/history")

    @tool
    def record_decision(
        decision: Literal["approve", "decline", "refer"],
        payout: float,
        rationale: str,
        policy_section: str,
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
        return call("POST", f"/api/claims/{claim_id}/decision", body)

    @tool
    def pay_claim(amount: float) -> str:
        """Pay the claim its approved payout, in US dollars."""
        return call("POST", f"/api/claims/{claim_id}/payment", {"amount": amount})

    return [get_claim, get_policy, get_claim_history, record_decision, pay_claim]


def model() -> ChatOpenAI:
    """Return the model named in MODEL_NAME, or GPT-6 Luna by default."""
    name = os.getenv("MODEL_NAME")
    return ChatOpenAI(
        model=name or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if name else "low",
    )


def messages(updates: Iterator[Any]) -> Iterator[BaseMessage]:
    """Return the new messages from the agent's stream of updates."""
    for update in updates:
        for node in update.values():
            yield from node["messages"]


def steps(message: BaseMessage) -> list[dict[str, str]]:
    """Turn a message from the agent into steps for the dashboard."""
    if isinstance(message, ToolMessage):
        return [
            {"kind": "tool_result", "name": str(message.name), "content": message.text}
        ]
    if not isinstance(message, AIMessage):
        return []
    said = [{"kind": "message", "name": "agent", "content": message.text}]
    return (said if message.text else []) + [
        {"kind": "tool_call", "name": made["name"], "content": json.dumps(made["args"])}
        for made in message.tool_calls
    ]


def run(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> str:
    """Run the agent on one claim, posting each step, and return its final reply."""
    with backend() as client:
        client.post(f"/api/claims/{claim_id}/start").raise_for_status()
        instructions = client.get("/api/instructions").raise_for_status().json()
        agent = create_agent(
            llm or model(),
            tools=make_tools(claim_id),
            system_prompt=instructions["instructions"],
        )
        updates = agent.stream(
            {"messages": [{"role": "user", "content": f"Decide claim {claim_id}."}]},
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="updates",
        )
        reply = ""
        for message in messages(updates):
            for step in steps(message):
                client.post(
                    f"/api/claims/{claim_id}/steps", json=step
                ).raise_for_status()
            if isinstance(message, AIMessage):
                reply = message.text
    return reply
