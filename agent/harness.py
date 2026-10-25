"""The agent harness: the model, the agents built on it and the steps they take."""

import json
import os
from collections.abc import Callable, Iterator, Sequence
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ToolCallRequest,
    ToolErrorMiddleware,
    after_model,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime
from pydantic import SecretStr

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "deepseek/deepseek-v4.1-flash"

Step = dict[str, str]


def model() -> ChatOpenAI:
    """Return the model named in MODEL_NAME, or DeepSeek V4.1 Flash by default."""
    name = os.getenv("MODEL_NAME")
    return ChatOpenAI(
        model=name or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if name else "low",
        timeout=120,
        max_retries=5,
    )


def refusals(refused: type[Exception]) -> ToolErrorMiddleware:
    """Send a tool's `refused` errors back to the model as text; others fail the run."""

    def tell_model(error: Exception, _: ToolCallRequest) -> str | None:
        return str(error) if isinstance(error, refused) else None

    return ToolErrorMiddleware(tell_model)


def finish_check(
    reminder: Callable[[Any], str | None], reminders: int = 2
) -> AgentMiddleware[Any, Any]:
    """Send the agent back when it tries to finish and reminder(context) has work
    for it, at most `reminders` times."""
    sent = 0

    @after_model(can_jump_to=["model"])
    def check(state: AgentState[Any], runtime: Runtime[Any]) -> dict[str, Any] | None:
        nonlocal sent
        last = state["messages"][-1]
        if not isinstance(last, AIMessage) or last.tool_calls or sent == reminders:
            return None
        text = reminder(runtime.context)
        if text is None:
            return None
        sent += 1
        return {"messages": [HumanMessage(text)], "jump_to": "model"}

    return check


def create(
    llm: BaseChatModel,
    tools: Sequence[BaseTool],
    instructions: str,
    context_schema: type,
    middleware: Sequence[AgentMiddleware[Any, Any]],
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Build an agent with its instructions, the type of its context and middleware."""
    return create_agent(
        llm,
        tools=tools,
        system_prompt=instructions,
        context_schema=context_schema,
        middleware=middleware,
    )


def messages(updates: Iterator[Any]) -> Iterator[BaseMessage]:
    """Return the new messages from the agent's stream of updates."""
    for update in updates:
        for node in update.values():
            # A middleware hook that changes nothing sends None.
            yield from (node or {}).get("messages", [])


def steps(message: BaseMessage) -> list[Step]:
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


def config(thread_id: str, step_limit: int) -> RunnableConfig:
    """Configure one run of an agent: its thread and its limit on graph steps."""
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": step_limit}


def run(
    agent: CompiledStateGraph[Any, Any, Any, Any],
    prompt: str,
    context: object,
    settings: RunnableConfig,
    record: Callable[[Step], object],
) -> str:
    """Run an agent from a fresh history, recording each step, and return its reply."""
    updates = agent.stream(
        {"messages": [{"role": "user", "content": prompt}]},
        config=settings,
        context=context,
        stream_mode="updates",
    )
    reply = ""
    for message in messages(updates):
        for step in steps(message):
            record(step)
        if isinstance(message, AIMessage):
            reply = message.text
    return reply
