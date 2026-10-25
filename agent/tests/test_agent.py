import json

from langchain_core.messages import AIMessage, SystemMessage

from agent import harness, tools
from agent.tests.conftest import calls, decides, stub
from backend.tests.conftest import new_run

DECISION = {"rationale": "Covered.", "policy_section": "Section 3, Trip Delay"}


def test_approval_within_the_limit_is_paid(api):
    llm = stub(
        calls(("get_claim", {})),
        calls(
            ("get_policy", {"policy_id": "POL-2001"}),
            ("get_claim_history", {"customer_id": "CUS-3001"}),
        ),
        calls(("record_decision", {"decision": "approve", "payout": 420} | DECISION)),
        calls(("pay_claim", {"amount": 420})),
        AIMessage(content="Approved and paid $420.00."),
    )
    line = tools.work(new_run(api), "CLM-1001", llm)
    assert line == "CLM-1001 approve $420.00, paid"

    claim = api.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "decided"
    assert claim["paid_amount"] == 420

    steps = api.get("/api/claims/CLM-1001/steps").json()
    kinds = [step["kind"] for step in steps]
    assert kinds.count("tool_call") == kinds.count("tool_result") == 5
    assert steps[0] == {
        "step_id": steps[0]["step_id"],
        "kind": "tool_call",
        "name": "get_claim",
        "content": "{}",
    }
    assert "My flight home from Rome" in steps[1]["content"]
    assert steps[-1]["kind"] == "message"
    assert steps[-1]["content"] == "Approved and paid $420.00."


def test_payment_over_the_limit_is_refused(api):
    llm = stub(
        calls(("get_claim", {})),
        calls(("record_decision", {"decision": "approve", "payout": 3750} | DECISION)),
        calls(("pay_claim", {"amount": 3750})),
        AIMessage(content="Approved; the payment waits for sign-off."),
    )
    line = tools.work(new_run(api), "CLM-1003", llm)
    assert line == "CLM-1003 approve $3,750.00, waiting for sign-off"

    claim = api.get("/api/claims/CLM-1003").json()
    assert claim["status"] == "waiting_for_sign_off"
    assert claim["paid_amount"] is None
    refusal = api.get("/api/claims/CLM-1003/steps").json()[-2]
    assert refusal["name"] == "pay_claim"
    assert "need a handler's sign-off" in refusal["content"]


def test_system_prompt_comes_from_the_api(api):
    llm = stub(*decides())
    tools.work(new_run(api), "CLM-1001", llm)
    system = llm.prompts[0][0]
    assert isinstance(system, SystemMessage)
    assert system.content == api.get("/api/instructions").json()["claim"]


def test_the_agent_reads_the_sections_it_needs(api):
    llm = stub(
        calls(("list_sections", {})),
        calls(("read_section", {"document": "claims_manual", "section": 7})),
        calls(("read_section", {"document": "policy_wording", "section": 99})),
        *decides(),
    )
    tools.work(new_run(api), "CLM-1001", llm)

    steps = api.get("/api/claims/CLM-1001/steps").json()
    assert [step["name"] for step in steps[:4]] == [
        "list_sections",
        "list_sections",
        "read_section",
        "read_section",
    ]
    assert "Interpretation notes" in steps[1]["content"]
    assert json.loads(steps[3]["content"])["title"] == "Interpretation notes"
    assert "Wild animals" in json.loads(steps[3]["content"])["text"]
    assert "There is no section 99" in steps[5]["content"]


def test_a_claim_agent_that_stops_without_a_decision_is_released(api):
    llm = stub(AIMessage(content="I am not sure."))
    line = tools.work(new_run(api), "CLM-1001", llm)
    assert line == (
        "CLM-1001 failed: The agent finished without a decision. "
        "Back in the queue after attempt 1"
    )
    assert api.get("/api/claims/CLM-1001").json()["status"] == "waiting"


def test_a_claim_agent_that_loops_is_released(api):
    llm = stub(*[calls(("list_sections", {})) for _ in range(40)])
    line = tools.work(new_run(api), "CLM-1001", llm)
    assert line.startswith("CLM-1001 failed: GraphRecursionError")
    assert api.get("/api/claims/CLM-1001").json()["status"] == "waiting"


def test_a_failure_after_the_decision_is_not_retried(api):
    approval = {"decision": "approve", "payout": 420} | DECISION
    llm = stub(calls(("record_decision", approval)), TimeoutError("Too slow"))
    line = tools.work(new_run(api), "CLM-1001", llm)
    assert line == "CLM-1001 approve $420.00, not paid"
    claim = api.get("/api/claims/CLM-1001").json()
    assert (claim["status"], claim["attempts"]) == ("decided", 1)


def test_each_agent_has_its_tools_and_none_signs_off():
    assert [tool.name for tool in tools.QUEUE_TOOLS] == [
        "get_queue",
        "write_todos",
        "work_claim",
    ]
    assert [tool.name for tool in tools.CLAIM_TOOLS] == [
        "get_claim",
        "get_policy",
        "get_claim_history",
        "list_sections",
        "read_section",
        "record_decision",
        "pay_claim",
    ]


def test_no_claim_tool_takes_the_claim_id():
    for tool in tools.CLAIM_TOOLS:
        assert not {"claim_id", "run_id"} & tool.args.keys(), tool.name


def test_a_reply_with_text_and_tool_calls_makes_both_steps():
    message = AIMessage(
        content="Let me read it.",
        tool_calls=[{"name": "get_claim", "args": {}, "id": "1"}],
    )
    assert [step["kind"] for step in harness.steps(message)] == [
        "message",
        "tool_call",
    ]


def test_model_name(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    default = harness.model()
    assert default.model_name == "deepseek/deepseek-v4.1-flash"
    assert default.reasoning_effort == "low"
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    chosen = harness.model()
    assert chosen.model_name == "openrouter/free"
    assert chosen.reasoning_effort is None
