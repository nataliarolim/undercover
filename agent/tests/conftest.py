from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from agent import api as backend_api
from backend.main import app
from backend.seed import seed


class StubModel(BaseChatModel):
    """A chat model that gives scripted replies, or raises scripted errors, and
    keeps the prompts it was sent."""

    replies: list[Any]
    prompts: list[list[BaseMessage]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "stub"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.prompts.append(messages)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return ChatResult(generations=[ChatGeneration(message=reply)])


def calls(*tool_calls: tuple[str, dict[str, Any]]) -> AIMessage:
    """A reply from the model that calls tools."""
    return AIMessage(
        content="",
        tool_calls=[
            {"name": name, "args": args, "id": str(n)}
            for n, (name, args) in enumerate(tool_calls)
        ],
    )


def stub(*replies: AIMessage | Exception) -> StubModel:
    return StubModel(replies=list(replies))


def decides(decision: str = "decline", payout: float = 0) -> list[AIMessage]:
    """A claim agent's replies that record a decision and finish."""
    body = {
        "decision": decision,
        "payout": payout,
        "rationale": "The wording settles it.",
        "policy_section": "Section 3, Trip Delay",
    }
    return [calls(("record_decision", body)), AIMessage(content="Decided.")]


@pytest.fixture
def api(tmp_path, monkeypatch):
    """Point the agent at a backend on a freshly seeded database."""
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "test.db"))
    seed()
    monkeypatch.setattr(
        backend_api, "client", lambda: TestClient(app, base_url="http://test/api")
    )
    return TestClient(app)
