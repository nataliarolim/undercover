import pytest


def test_list_claims(client):
    claims = client.get("/api/claims").json()
    assert len(claims) == 25
    assert claims[0] == {
        "claim_id": "CLM-1001",
        "summary": "Flight home canceled by the airline, rebooked the next morning",
        "claim_type": "trip_delay",
        "amount_claimed": 420.0,
        "status": "waiting",
        "decision": None,
        "payout": None,
    }


def test_get_claim(client):
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["story"].startswith("My flight home from Rome")
    assert len(claim["items"]) == 3
    assert len(claim["documents"]) == 4
    assert claim["status"] == "waiting"
    assert claim["decision"] is None
    assert claim["paid_amount"] is None


def test_get_policy(client):
    policy = client.get("/api/policies/POL-2001").json()
    assert policy["plan"] == "premium"
    assert policy["trip"]["returns_on"] == "2026-06-18"
    assert policy["travelers"] == ["Maya Patel"]


def test_claim_history_leaves_out_contact_details(client):
    history = client.get("/api/customers/CUS-3001/history").json()
    assert history["name"] == "Maya Patel"
    assert history["customer_since"] == "2023-04-11"
    assert [c["claim_id"] for c in history["previous_claims"]] == ["CLM-0412"]
    assert not {"email", "phone", "date_of_birth", "address"} & history.keys()


def test_list_handlers(client):
    handlers = client.get("/api/handlers").json()
    assert handlers[0] == {
        "handler_id": "HND-01",
        "name": "Dana Whitfield",
        "role": "Senior Claims Handler",
    }


@pytest.mark.parametrize(
    "path",
    [
        "/api/claims/CLM-0000",
        "/api/policies/POL-0000",
        "/api/customers/CUS-0000/history",
    ],
)
def test_unknown_ids_are_not_found(client, path):
    response = client.get(path)
    assert response.status_code == 404
    assert response.json()["detail"].startswith("There is no ")
