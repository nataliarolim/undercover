from backend.tests.conftest import new_run

ERROR = "ReadTimeout: the model took too long"


def start(client, claim_id, run_id):
    return client.post(f"/api/claims/{claim_id}/start", json={"run_id": run_id})


def release(client, claim_id):
    return client.post(f"/api/claims/{claim_id}/release", json={"error": ERROR})


def decide(client, claim_id, decision="approve", payout=400):
    return client.post(
        f"/api/claims/{claim_id}/decision",
        json={
            "decision": decision,
            "payout": payout,
            "rationale": "Covered.",
            "policy_section": "Section 3, Trip Delay",
        },
    )


def pay(client, claim_id, amount=400):
    return client.post(f"/api/claims/{claim_id}/payment", json={"amount": amount})


def finish(client, run_id, summary="Five claims decided."):
    return client.post(f"/api/runs/{run_id}/finish", json={"summary": summary})


def claim(client, claim_id):
    return client.get(f"/api/claims/{claim_id}").json()


def queue(client, run_id):
    return [c["claim_id"] for c in client.get(f"/api/runs/{run_id}/queue").json()]


def test_the_cap_on_a_run(client):
    run = new_run(client, cap=2)
    assert start(client, "CLM-1001", run).status_code == 200
    assert start(client, "CLM-1002", run).status_code == 200
    third = start(client, "CLM-1003", run)
    assert third.status_code == 409
    assert third.json()["detail"] == f"Run {run} has reached its cap of 2"
    release(client, "CLM-1001")
    assert start(client, "CLM-1001", run).status_code == 200


def test_a_claim_starts_only_in_a_running_run(client):
    first = new_run(client)
    finish(client, first)
    assert start(client, "CLM-1001", first).json()["detail"] == (
        f"Run {first} is finished"
    )
    second = new_run(client)
    new_run(client)
    assert start(client, "CLM-1001", second).json()["detail"] == (
        f"Run {second} is stopped"
    )
    assert start(client, "CLM-1001", 99).status_code == 404


def test_attempts_count_each_start(client):
    run = new_run(client)
    assert start(client, "CLM-1001", run).json()["attempts"] == 1
    release(client, "CLM-1001")
    again = start(client, "CLM-1001", run).json()
    assert again["attempts"] == 2
    assert again["error"] is None


def test_a_failed_claim_goes_back_in_the_queue(client):
    run = new_run(client)
    start(client, "CLM-1001", run)
    released = release(client, "CLM-1001").json()
    assert released["status"] == "waiting"
    assert released["error"] == ERROR
    step = client.get("/api/claims/CLM-1001/steps").json()[-1]
    assert step == {
        "step_id": step["step_id"],
        "kind": "error",
        "name": "Attempt 1 of 2",
        "content": ERROR,
    }


def test_a_claim_that_fails_twice_is_left_for_a_handler(client):
    run = new_run(client)
    for _ in range(2):
        start(client, "CLM-1001", run)
        release(client, "CLM-1001")
    left = claim(client, "CLM-1001")
    assert left["status"] == "left_for_handler"
    assert left["error"] == ERROR
    assert start(client, "CLM-1001", run).status_code == 409


def test_a_claim_is_never_decided_or_paid_twice(client):
    run = new_run(client)
    assert release(client, "CLM-1001").status_code == 409
    start(client, "CLM-1001", run)
    decide(client, "CLM-1001")
    pay(client, "CLM-1001")
    refused = release(client, "CLM-1001")
    assert refused.status_code == 409
    assert refused.json()["detail"] == "Claim CLM-1001 is not in progress"
    assert decide(client, "CLM-1001", "decline", 0).status_code == 409
    assert pay(client, "CLM-1001").status_code == 409
    paid = claim(client, "CLM-1001")
    assert (paid["status"], paid["decision"], paid["paid_amount"]) == (
        "decided",
        "approve",
        400,
    )


def test_starting_a_run_stops_the_last_and_releases_its_claims(client):
    first = new_run(client)
    start(client, "CLM-1001", first)
    second = new_run(client)
    assert client.get("/api/runs/latest").json()["run_id"] == second
    released = claim(client, "CLM-1001")
    assert released["status"] == "waiting"
    assert released["attempts"] == 1
    assert released["error"] == "The run stopped before the claim was decided"
    assert queue(client, first) == []


def test_the_to_do_list_is_stored(client):
    run = new_run(client)
    todos = [
        {"content": "Decide CLM-1001", "status": "done"},
        {"content": "Decide CLM-1002", "status": "in_progress"},
        {"content": "Decide CLM-1003", "status": "to_do"},
        {"content": "Decide CLM-1004", "status": "left_for_handler"},
    ]
    response = client.put(f"/api/runs/{run}/todos", json={"todos": todos})
    assert response.status_code == 200
    assert client.get("/api/runs/latest").json()["todos"] == todos

    unknown = [{"content": "Decide CLM-1005", "status": "blocked"}]
    response = client.put(f"/api/runs/{run}/todos", json={"todos": unknown})
    assert response.status_code == 422
    finish(client, run)
    response = client.put(f"/api/runs/{run}/todos", json={"todos": todos})
    assert response.status_code == 409


def test_the_queue_a_run_may_still_take(client):
    run = new_run(client, cap=2)
    assert len(queue(client, run)) == 25
    start(client, "CLM-1001", run)
    start(client, "CLM-1002", run)
    assert queue(client, run) == []
    release(client, "CLM-1001")
    decide(client, "CLM-1002")
    assert queue(client, run) == ["CLM-1001"]
    start(client, "CLM-1001", run)
    release(client, "CLM-1001")
    assert queue(client, run) == []


def test_finish_run(client):
    assert client.get("/api/runs/latest").json() is None
    run = new_run(client)
    finished = finish(client, run).json()
    assert finished["status"] == "finished"
    assert finished["summary"] == "Five claims decided."
    assert finished["finished_at"] is not None
    assert finish(client, run).status_code == 409
