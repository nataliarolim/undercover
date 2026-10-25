import pytest

CLAIM = "CLM-1003"


def start(client, claim_id=CLAIM):
    return client.post(f"/api/claims/{claim_id}/start")


def decide(client, decision, payout, claim_id=CLAIM):
    return client.post(
        f"/api/claims/{claim_id}/decision",
        json={
            "decision": decision,
            "payout": payout,
            "rationale": "The wording covers it.",
            "policy_section": "Section 7, Emergency Medical",
        },
    )


def pay(client, amount, claim_id=CLAIM):
    return client.post(f"/api/claims/{claim_id}/payment", json={"amount": amount})


def sign_off(client, handler_id="HND-01", claim_id=CLAIM):
    return client.post(
        f"/api/claims/{claim_id}/sign-off", json={"handler_id": handler_id}
    )


def approve(client, payout):
    start(client)
    return decide(client, "approve", payout)


def test_start_claim(client):
    response = start(client)
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
    again = start(client)
    assert again.status_code == 409
    assert again.json()["detail"] == f"Claim {CLAIM} is not waiting"


@pytest.mark.parametrize("decision", ["decline", "refer"])
def test_decline_or_refer_is_decided(client, decision):
    start(client)
    claim = decide(client, decision, 0).json()
    assert claim["status"] == "decided"
    assert claim["decision"] == decision
    assert claim["rationale"] == "The wording covers it."
    assert claim["policy_section"] == "Section 7, Emergency Medical"


@pytest.mark.parametrize(
    ("decision", "payout"), [("decline", 50), ("refer", 10), ("approve", 0)]
)
def test_payout_must_fit_the_decision(client, decision, payout):
    start(client)
    assert decide(client, decision, payout).status_code == 422


def test_approval_within_the_limit_is_decided(client):
    assert approve(client, 1000).json()["status"] == "decided"


def test_approval_over_the_limit_waits_for_sign_off(client):
    claim = approve(client, 1000.01).json()
    assert claim["status"] == "waiting_for_sign_off"
    assert claim["payout"] == 1000.01


def test_payout_is_rounded_to_cents(client):
    assert approve(client, 420.004).json()["payout"] == 420.0


def test_decision_needs_a_claim_in_progress(client):
    assert decide(client, "decline", 0).status_code == 409
    start(client)
    decide(client, "decline", 0)
    second = decide(client, "approve", 100)
    assert second.status_code == 409
    assert second.json()["detail"] == f"Claim {CLAIM} is not in progress"


def test_payment_up_to_the_limit(client):
    approve(client, 1000)
    response = pay(client, 1000)
    assert response.status_code == 200
    assert response.json()["paid_amount"] == 1000


def test_payment_over_the_limit_is_refused(client):
    approve(client, 1000.01)
    response = pay(client, 1000.01)
    assert response.status_code == 403
    assert response.json() == {
        "detail": "Payouts over $1,000.00 need a handler's sign-off"
    }
    assert client.get(f"/api/claims/{CLAIM}").json()["paid_amount"] is None


def test_splitting_a_payment_is_refused(client):
    approve(client, 3750)
    assert pay(client, 999).status_code == 403


def test_payment_must_match_the_payout(client):
    approve(client, 400)
    response = pay(client, 500)
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "The amount must be the approved payout of $400.00"
    )


def test_payment_needs_an_approval(client):
    assert pay(client, 100).status_code == 409
    start(client)
    decide(client, "decline", 0)
    response = pay(client, 100)
    assert response.status_code == 409
    assert response.json()["detail"] == "Only an approval can be paid"


def test_claim_is_paid_once(client):
    approve(client, 400)
    pay(client, 400)
    second = pay(client, 400)
    assert second.status_code == 409
    assert second.json()["detail"] == f"Claim {CLAIM} is already paid"


def test_sign_off_pays_the_payout(client):
    approve(client, 3750)
    claim = sign_off(client).json()
    assert claim["status"] == "decided"
    assert claim["paid_amount"] == 3750
    assert claim["signed_off_by"] == "HND-01"


def test_sign_off_needs_a_claim_waiting_for_it(client):
    approve(client, 400)
    response = sign_off(client)
    assert response.status_code == 409
    assert response.json()["detail"] == f"Claim {CLAIM} is not waiting for sign-off"


def test_sign_off_needs_a_handler(client):
    approve(client, 3750)
    assert sign_off(client, handler_id="HND-99").status_code == 404


def test_steps_come_back_in_order(client):
    for n in range(3):
        response = client.post(
            f"/api/claims/{CLAIM}/steps",
            json={"kind": "tool_call", "name": "get_claim", "content": str(n)},
        )
        assert response.status_code == 201
    steps = client.get(f"/api/claims/{CLAIM}/steps").json()
    assert [step["content"] for step in steps] == ["0", "1", "2"]
    assert steps[0]["step_id"] < steps[1]["step_id"] < steps[2]["step_id"]


def test_steps_need_a_claim(client):
    assert client.get("/api/claims/CLM-0000/steps").status_code == 404
