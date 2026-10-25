from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult
from pydantic import Field

from agent import main
from backend.main import app
from backend.seed import seed


class StubModel(GenericFakeChatModel):
    """A chat model that gives scripted replies and keeps the prompts it was sent."""

    prompts: list[list[BaseMessage]] = Field(default_factory=list)

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
        return super()._generate(messages, stop, run_manager, **kwargs)


def calls(*tool_calls: tuple[str, dict[str, Any]]) -> AIMessage:
    """A reply from the model that calls tools."""
    return AIMessage(
        content="",
        tool_calls=[
            {"name": name, "args": args, "id": str(n)}
            for n, (name, args) in enumerate(tool_calls)
        ],
    )


def stub(*replies: AIMessage) -> StubModel:
    return StubModel(messages=iter(replies))


@pytest.fixture
def api(tmp_path, monkeypatch):
    """Point the agent at a backend on a freshly seeded database."""
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "test.db"))
    seed()
    monkeypatch.setattr(main, "backend", lambda: TestClient(app))
    return TestClient(app)
