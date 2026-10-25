"""Claims, the records they draw on, and the workflow that decides them."""

import json
import sqlite3

from fastapi import APIRouter, HTTPException, status

from backend.db import Database, find, update
from backend.models import (
    Claim,
    ClaimHistory,
    ClaimSummary,
    Decision,
    Failure,
    Handler,
    NewStep,
    Payment,
    Policy,
    SignOff,
    StartClaim,
    Step,
)
from backend.seed import DATA

COMPANY = json.loads((DATA / "company.json").read_text(encoding="utf-8"))
PAYOUT_LIMIT: float = COMPANY["payout_approval_limit"]
ATTEMPTS = 2

router = APIRouter()


def load_claim(row: sqlite3.Row) -> Claim:
    """Combine a claim's record with where it stands."""
    return Claim.model_validate(json.loads(row["record"]) | dict(row))


def find_claim(db: sqlite3.Connection, claim_id: str) -> Claim:
    """Return the claim, or a 404."""
    row = find(db, "SELECT * FROM claims WHERE claim_id = ?", claim_id, "claim")
    return load_claim(row)


def release_in_progress(db: sqlite3.Connection, claim_id: str, error: str) -> bool:
    """Put a claim in progress back in the queue, or leave it for a handler after its
    last attempt, recording the error as a step. False if it wasn't in progress."""
    row = db.execute(
        "UPDATE claims SET error = ?, status = CASE WHEN attempts < ? "
        "THEN 'waiting' ELSE 'left_for_handler' END "
        "WHERE claim_id = ? AND status = 'in_progress' RETURNING attempts",
        (error, ATTEMPTS, claim_id),
    ).fetchone()
    if row is None:
        return False
    db.execute(
        "INSERT INTO steps (claim_id, kind, name, content) VALUES (?, 'error', ?, ?)",
        (claim_id, f"Attempt {row['attempts']} of {ATTEMPTS}", error),
    )
    return True


def dollars(amount: float) -> str:
    """Format an amount as US dollars, such as $1,250.00."""
    return f"${amount:,.2f}"


@router.get("/claims", operation_id="list_claims")
def list_claims(db: Database) -> list[ClaimSummary]:
    """List the claims queue with where each claim stands."""
    rows = db.execute("SELECT * FROM claims ORDER BY claim_id").fetchall()
    return [load_claim(row) for row in rows]


@router.get("/claims/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str, db: Database) -> Claim:
    """Get a claim in full, with the decision on it."""
    return find_claim(db, claim_id)


@router.get("/policies/{policy_id}", operation_id="get_policy")
def get_policy(policy_id: str, db: Database) -> Policy:
    """Get a policy: the plan, the add-ons, the trip and the travelers."""
    sql = "SELECT record FROM policies WHERE policy_id = ?"
    row = find(db, sql, policy_id, "policy")
    return Policy.model_validate_json(row["record"])


@router.get("/customers/{customer_id}/history", operation_id="get_claim_history")
def get_claim_history(customer_id: str, db: Database) -> ClaimHistory:
    """Get a customer's name and earlier claims, without their contact details."""
    sql = "SELECT record FROM customers WHERE customer_id = ?"
    row = find(db, sql, customer_id, "customer")
    return ClaimHistory.model_validate_json(row["record"])


@router.get("/handlers", operation_id="list_handlers")
def list_handlers(db: Database) -> list[Handler]:
    """List the claims handlers."""
    rows = db.execute("SELECT record FROM handlers ORDER BY handler_id").fetchall()
    return [Handler.model_validate_json(row["record"]) for row in rows]


@router.post("/claims/{claim_id}/start", operation_id="start_claim")
def start_claim(claim_id: str, start: StartClaim, db: Database) -> Claim:
    """Start a waiting claim in a running run, within the run's cap."""
    claim = find_claim(db, claim_id)
    run = find(db, "SELECT * FROM runs WHERE run_id = ?", start.run_id, "run")
    if run["status"] != "running":
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Run {start.run_id} is {run['status']}"
        )
    if claim.status != "waiting":
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Claim {claim_id} is not waiting"
        )
    # One statement, so two starts at once can't both pass the cap.
    update(
        db,
        "UPDATE claims SET status = 'in_progress', attempts = attempts + 1, "
        "error = NULL, run_id = :run WHERE claim_id = :claim AND status = 'waiting' "
        "AND (run_id IS :run OR (SELECT COUNT(*) FROM claims WHERE run_id = :run) "
        "< (SELECT cap FROM runs WHERE run_id = :run))",
        {"run": start.run_id, "claim": claim_id},
        f"Run {start.run_id} has reached its cap of {run['cap']}",
    )
    return find_claim(db, claim_id)


@router.post("/claims/{claim_id}/release", operation_id="release_claim")
def release_claim(claim_id: str, failure: Failure, db: Database) -> Claim:
    """Release a claim that failed in progress, back to waiting or to a handler."""
    find_claim(db, claim_id)
    if not release_in_progress(db, claim_id, failure.error):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Claim {claim_id} is not in progress"
        )
    return find_claim(db, claim_id)


@router.post("/claims/{claim_id}/steps", operation_id="add_step", status_code=201)
def add_step(claim_id: str, step: NewStep, db: Database) -> Step:
    """Record a step the agent took on a claim."""
    find_claim(db, claim_id)
    ((step_id,),) = db.execute(
        "INSERT INTO steps (claim_id, kind, name, content) VALUES (?, ?, ?, ?) "
        "RETURNING step_id",
        (claim_id, step.kind, step.name, step.content),
    ).fetchall()
    return Step(step_id=step_id, **step.model_dump())


@router.get("/claims/{claim_id}/steps", operation_id="list_steps")
def list_steps(claim_id: str, db: Database) -> list[Step]:
    """List the steps the agent took on a claim, in order."""
    find_claim(db, claim_id)
    rows = db.execute(
        "SELECT step_id, kind, name, content FROM steps "
        "WHERE claim_id = ? ORDER BY step_id",
        (claim_id,),
    ).fetchall()
    return [Step.model_validate(dict(row)) for row in rows]


@router.post("/claims/{claim_id}/decision", operation_id="record_decision")
def record_decision(claim_id: str, decision: Decision, db: Database) -> Claim:
    """Record the decision on a claim in progress."""
    find_claim(db, claim_id)
    over_limit = decision.payout > PAYOUT_LIMIT
    update(
        db,
        "UPDATE claims SET status = ?, decision = ?, payout = ?, rationale = ?, "
        "policy_section = ? WHERE claim_id = ? AND status = 'in_progress'",
        (
            "waiting_for_sign_off" if over_limit else "decided",
            decision.decision,
            decision.payout,
            decision.rationale,
            decision.policy_section,
            claim_id,
        ),
        f"Claim {claim_id} is not in progress",
    )
    return find_claim(db, claim_id)


@router.post("/claims/{claim_id}/payment", operation_id="pay_claim")
def pay_claim(claim_id: str, payment: Payment, db: Database) -> Claim:
    """Pay an approved claim its payout, which must be within the limit."""
    claim = find_claim(db, claim_id)
    if payment.amount > PAYOUT_LIMIT or claim.status == "waiting_for_sign_off":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Payouts over {dollars(PAYOUT_LIMIT)} need a handler's sign-off",
        )
    if claim.decision != "approve" or claim.payout is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only an approval can be paid")
    if payment.amount != claim.payout:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"The amount must be the approved payout of {dollars(claim.payout)}",
        )
    update(
        db,
        "UPDATE claims SET paid_amount = ? "
        "WHERE claim_id = ? AND status = 'decided' AND paid_amount IS NULL",
        (payment.amount, claim_id),
        f"Claim {claim_id} is already paid",
    )
    return find_claim(db, claim_id)


@router.post("/claims/{claim_id}/sign-off", operation_id="sign_off_claim")
def sign_off_claim(claim_id: str, sign_off: SignOff, db: Database) -> Claim:
    """Sign off an approval over the limit, which pays its payout."""
    find_claim(db, claim_id)
    sql = "SELECT handler_id FROM handlers WHERE handler_id = ?"
    find(db, sql, sign_off.handler_id, "handler")
    update(
        db,
        "UPDATE claims SET status = 'decided', paid_amount = payout, "
        "signed_off_by = ? WHERE claim_id = ? AND status = 'waiting_for_sign_off'",
        (sign_off.handler_id, claim_id),
        f"Claim {claim_id} is not waiting for sign-off",
    )
    return find_claim(db, claim_id)
