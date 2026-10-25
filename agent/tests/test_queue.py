import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent import __main__ as cli
from agent import api as backend_api
from agent.tests.conftest import calls, decides, stub

TIMEOUT = TimeoutError("The model took too long")


def work(claim_id):
    return calls(("work_claim", {"claim_id": claim_id}))


def todos(*items):
    return calls(
        ("write_todos", {"todos": [{"content": c, "status": s} for c, s in items]})
    )


def claim(api, claim_id):
    return api.get(f"/api/claims/{claim_id}").json()


def latest_run(api):
    return api.get("/api/runs/latest").json()


def test_one_run_works_the_queue(api, capsys):
    done = [("Decide CLM-1001", "done"), ("Decide CLM-1002", "done")]
    queue = stub(
        todos(("Decide CLM-1001", "to_do"), ("Decide CLM-1002", "to_do")),
        work("CLM-1001"),
        work("CLM-1002"),
        todos(*done),
        AIMessage(content="Two claims declined."),
    )
    summary = cli.work_queue(2, queue, stub(*decides(), *decides()))

    assert summary == "Two claims declined."
    assert claim(api, "CLM-1001")["status"] == "decided"
    assert claim(api, "CLM-1002")["status"] == "decided"
    run = latest_run(api)
    assert (run["status"], run["summary"]) == ("finished", "Two claims declined.")
    assert run["todos"] == [{"content": c, "status": s} for c, s in done]
    assert capsys.readouterr().out == "CLM-1001 decline\nCLM-1002 decline\n"


def test_each_claim_agent_starts_fresh(api):
    claims = stub(*decides(), *decides())
    queue = stub(work("CLM-1001"), work("CLM-1002"), AIMessage(content="Done."))
    cli.work_queue(2, queue, claims)

    firsts = [p for p in claims.prompts if isinstance(p[-1], HumanMessage)]
    assert [[type(m).__name__ for m in p] for p in firsts] == [
        ["SystemMessage", "HumanMessage"]
    ] * 2
    assert [p[-1].content for p in firsts] == [
        "Decide claim CLM-1001.",
        "Decide claim CLM-1002.",
    ]


def test_the_cap_on_a_run(api):
    queue = stub(
        work("CLM-1001"),
        work("CLM-1002"),
        work("CLM-1003"),
        AIMessage(content="Done."),
    )
    cli.work_queue(2, queue, stub(*decides(), *decides()))

    refusal = queue.prompts[3][-1]
    assert isinstance(refusal, ToolMessage)
    assert "Run 1 has reached its cap of 2" in refusal.text
    statuses = [c["status"] for c in api.get("/api/claims").json()]
    assert statuses.count("waiting") == 23
    assert claim(api, "CLM-1003")["attempts"] == 0


def test_a_failed_claim_does_not_stop_the_run(api, capsys):
    queue = stub(
        work("CLM-1001"),
        work("CLM-1002"),
        *[AIMessage(content="Leaving CLM-1001 for later.") for _ in range(3)],
    )
    claims = stub(calls(("get_claim", {})), TIMEOUT, *decides())
    cli.work_queue(2, queue, claims)

    failed = claim(api, "CLM-1001")
    assert (failed["status"], failed["attempts"]) == ("waiting", 1)
    assert failed["error"] == "TimeoutError: The model took too long"
    assert claim(api, "CLM-1002")["status"] == "decided"
    steps = api.get("/api/claims/CLM-1001/steps").json()
    assert [step["kind"] for step in steps] == ["tool_call", "tool_result", "error"]
    assert latest_run(api)["status"] == "finished"
    assert capsys.readouterr().out.startswith(
        "CLM-1001 failed: TimeoutError: The model took too long. "
        "Back in the queue after attempt 1\nCLM-1002 decline\n"
    )


def test_a_failed_claim_goes_back_in_the_queue_and_is_tried_again(api):
    queue = stub(work("CLM-1001"), work("CLM-1001"), AIMessage(content="Done."))
    cli.work_queue(1, queue, stub(TIMEOUT, *decides()))

    retried = claim(api, "CLM-1001")
    assert (retried["status"], retried["attempts"]) == ("decided", 2)
    assert queue.prompts[2][-1].text == "CLM-1001 decline"


def test_a_claim_that_fails_twice_is_left_for_a_handler(api, capsys):
    queue = stub(
        work("CLM-1001"),
        work("CLM-1001"),
        AIMessage(content="CLM-1001 is left for a handler."),
    )
    cli.work_queue(1, queue, stub(TIMEOUT, TIMEOUT))

    assert claim(api, "CLM-1001")["status"] == "left_for_handler"
    assert latest_run(api)["status"] == "finished"
    assert capsys.readouterr().out.splitlines()[1] == (
        "CLM-1001 failed: TimeoutError: The model took too long. "
        "Left for a handler after 2 attempts"
    )


def test_the_check_for_missed_claims(api):
    queue = stub(
        AIMessage(content="Nothing to do."),
        work("CLM-1001"),
        AIMessage(content="CLM-1001 declined."),
    )
    summary = cli.work_queue(1, queue, stub(*decides()))

    reminder = queue.prompts[1][-1]
    assert isinstance(reminder, HumanMessage)
    assert reminder.text.startswith("Before you finish: CLM-1001, CLM-1002")
    assert claim(api, "CLM-1001")["status"] == "decided"
    assert summary == "CLM-1001 declined."


def test_the_check_for_missed_claims_reminds_at_most_twice(api):
    queue = stub(*[AIMessage(content="No.") for _ in range(3)])
    assert cli.work_queue(1, queue, stub()) == "No."
    assert len(queue.prompts) == 3
    assert latest_run(api)["status"] == "finished"


def test_a_cap_of_zero_is_refused_not_ignored(api):
    with pytest.raises(backend_api.Refused):
        cli.work_queue(0, stub(), stub())


def test_a_run_over_the_whole_queue_is_capped_at_its_size(api):
    queue = stub(*[AIMessage(content="No.") for _ in range(3)])
    cli.work_queue(None, queue, stub())
    assert latest_run(api)["cap"] == 25
