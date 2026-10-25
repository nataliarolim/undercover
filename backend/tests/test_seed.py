import inspect
import runpy

from backend.db import connect
from backend.seed import seed


def test_seed_loads_the_queue(client):
    claims = client.get("/api/claims").json()
    assert [claim["claim_id"] for claim in claims] == [
        f"CLM-{n}" for n in range(1001, 1026)
    ]
    assert {claim["status"] for claim in claims} == {"waiting"}


def test_reseed_resets_a_changed_claim(client):
    db = connect()
    db.execute("UPDATE claims SET status = 'decided' WHERE claim_id = 'CLM-1001'")
    db.close()
    assert client.get("/api/claims/CLM-1001").json()["status"] == "decided"
    seed()
    assert client.get("/api/claims/CLM-1001").json()["status"] == "waiting"


def test_first_start_creates_the_database(client, tmp_path):
    assert (tmp_path / "test.db").exists()
    assert len(client.get("/api/handlers").json()) == 3


def test_seed_command(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "command.db"))
    runpy.run_path(inspect.getfile(seed), run_name="__main__")
    assert capsys.readouterr().out == (
        "Seeded 25 claims, 50 policies, 49 customers, 3 handlers\n"
    )
