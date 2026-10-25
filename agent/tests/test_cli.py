import inspect
import runpy

import pytest

from agent import __main__ as cli
from agent import harness
from agent.tests.conftest import decides, stub


def test_named_claims_skip_the_queue_agent(api, monkeypatch, capsys):
    monkeypatch.setattr(harness, "model", lambda: stub(*decides("approve", 3750)))
    monkeypatch.setattr("sys.argv", ["agent", "CLM-1003"])
    runpy.run_path(inspect.getfile(cli), run_name="__main__")
    line = "CLM-1003 approve $3,750.00, waiting for sign-off"
    assert capsys.readouterr().out == f"{line}\n"
    run = api.get("/api/runs/latest").json()
    assert (run["cap"], run["status"], run["summary"]) == (1, "finished", line)


def test_a_named_claim_that_is_not_waiting_is_not_started(api, monkeypatch, capsys):
    monkeypatch.setattr(harness, "model", lambda: stub(*decides("approve", 3750)))
    cli.main(["CLM-1003"])
    cli.main(["CLM-1003"])
    assert capsys.readouterr().out.splitlines()[1] == (
        'CLM-1003 not started: {"detail":"Claim CLM-1003 is not waiting"}'
    )


@pytest.mark.parametrize(("argv", "cap"), [(["--cap", "5"], 5), ([], None)])
def test_the_queue_runs_with_its_cap(monkeypatch, capsys, argv, cap):
    runs = []
    monkeypatch.setattr(harness, "model", lambda: "model")
    monkeypatch.setattr(
        cli, "work_queue", lambda *args: runs.append(args) or "Summary."
    )
    cli.main(argv)
    assert runs == [(cap, "model", "model")]
    assert capsys.readouterr().out == "Summary.\n"
