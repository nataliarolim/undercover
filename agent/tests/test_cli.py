import inspect
import runpy

from agent import __main__ as cli
from agent import main


def test_works_only_waiting_claims(api, monkeypatch, capsys):
    api.post("/api/claims/CLM-1001/start")
    runs = []
    monkeypatch.setattr(main, "run", lambda claim_id, thread_id: runs.append(thread_id))
    cli.main([])
    assert len(runs) == 24
    assert len(set(runs)) == 24
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "CLM-1002 waiting with no decision"
    assert not any(line.startswith("CLM-1001") for line in lines)


def test_works_the_named_claims(api, monkeypatch, capsys):
    def decide(claim_id, thread_id):
        api.post(f"/api/claims/{claim_id}/start")
        api.post(
            f"/api/claims/{claim_id}/decision",
            json={
                "decision": "approve",
                "payout": 3750,
                "rationale": "Covered.",
                "policy_section": "Section 7, Emergency Medical",
            },
        )

    monkeypatch.setattr(main, "run", decide)
    monkeypatch.setattr("sys.argv", ["agent", "CLM-1003"])
    runpy.run_path(inspect.getfile(cli), run_name="__main__")
    assert capsys.readouterr().out == (
        "CLM-1003 waiting_for_sign_off approve $3,750.00\n"
    )
