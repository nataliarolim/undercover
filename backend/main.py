"""The UnderCover backend."""

import json
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status

from backend.db import database, database_path
from backend.models import (
    Claim,
    ClaimHistory,
    ClaimSummary,
    Decision,
    Handler,
    Instructions,
    NewStep,
    Payment,
    Policy,
    SignOff,
    Step,
)
from backend.seed import DATA, seed

INSTRUCTIONS = Path(__file__).parent / "instructions.md"
COMPANY = json.loads((DATA / "company.json").read_text(encoding="utf-8"))
PAYOUT_LIMIT: float = COMPANY["payout_approval_limit"]

Database = Annotated[sqlite3.Connection, Depends(database)]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Seed the database on the first start."""
    if not database_path().exists():
        seed()
    yield


app = FastAPI(title="UnderCover", lifespan=lifespan)


def find(db: sqlite3.Connection, sql: str, key: str, what: str) -> sqlite3.Row:
    """Return the one row the query finds for key, or a 404."""
    row = db.execute(sql, (key,)).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"There is no {what} {key}")
    return row


def load_claim(row: sqlite3.Row) -> Claim:
    """Combine a claim's record with where it stands."""
    return Claim.model_validate(json.loads(row["record"]) | dict(row))


def find_claim(db: sqlite3.Connection, claim_id: str) -> Claim:
    """Return the claim, or a 404."""
    row = find(db, "SELECT * FROM claims WHERE claim_id = ?", claim_id, "claim")
    return load_claim(row)


def update_claim(
    db: sqlite3.Connection, sql: str, params: tuple[object, ...], conflict: str
) -> None:
    """Run an update that only applies in the right status, or a 409."""
    if db.execute(sql, params).rowcount == 0:
        raise HTTPException(status.HTTP_409_CONFLICT, conflict)


def dollars(amount: float) -> str:
    """Format an amount as US dollars, such as $1,250.00."""
    return f"${amount:,.2f}"


@app.get("/api/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the backend is running."""
    return {"status": "ok"}


@app.get("/api/claims", operation_id="list_claims")
def list_claims(db: Database) -> list[ClaimSummary]:
    """List the claims queue with where each claim stands."""
    rows = db.execute("SELECT * FROM claims ORDER BY claim_id").fetchall()
    return [load_claim(row) for row in rows]


@app.get("/api/claims/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str, db: Database) -> Claim:
    """Get a claim in full, with the decision on it."""
    return find_claim(db, claim_id)


@app.get("/api/policies/{policy_id}", operation_id="get_policy")
def get_policy(policy_id: str, db: Database) -> Policy:
    """Get a policy: the plan, the add-ons, the trip and the travelers."""
    sql = "SELECT record FROM policies WHERE policy_id = ?"
    row = find(db, sql, policy_id, "policy")
    return Policy.model_validate_json(row["record"])


@app.get("/api/customers/{customer_id}/history", operation_id="get_claim_history")
def get_claim_history(customer_id: str, db: Database) -> ClaimHistory:
    """Get a customer's name and earlier claims, without their contact details."""
    sql = "SELECT record FROM customers WHERE customer_id = ?"
    row = find(db, sql, customer_id, "customer")
    return ClaimHistory.model_validate_json(row["record"])


@app.get("/api/handlers", operation_id="list_handlers")
def list_handlers(db: Database) -> list[Handler]:
    """List the claims handlers."""
    rows = db.execute("SELECT record FROM handlers ORDER BY handler_id").fetchall()
    return [Handler.model_validate_json(row["record"]) for row in rows]


@app.get("/api/instructions", operation_id="get_instructions")
def get_instructions() -> Instructions:
    """Get the agent's instructions, followed by the policy wording."""
    instructions = INSTRUCTIONS.read_text(encoding="utf-8")
    wording = (DATA / "policy_wording.md").read_text(encoding="utf-8")
    return Instructions(instructions=f"{instructions}\n{wording}")


@app.post("/api/claims/{claim_id}/start", operation_id="start_claim")
def start_claim(claim_id: str, db: Database) -> Claim:
    """Mark a waiting claim as in progress."""
    find_claim(db, claim_id)
    update_claim(
        db,
        "UPDATE claims SET status = 'in_progress' "
        "WHERE claim_id = ? AND status = 'waiting'",
        (claim_id,),
        f"Claim {claim_id} is not waiting",
    )
    return find_claim(db, claim_id)


@app.post("/api/claims/{claim_id}/steps", operation_id="add_step", status_code=201)
def add_step(claim_id: str, step: NewStep, db: Database) -> Step:
    """Record a step the agent took on a claim."""
    find_claim(db, claim_id)
    ((step_id,),) = db.execute(
        "INSERT INTO steps (claim_id, kind, name, content) VALUES (?, ?, ?, ?) "
        "RETURNING step_id",
        (claim_id, step.kind, step.name, step.content),
    ).fetchall()
    return Step(step_id=step_id, **step.model_dump())


@app.get("/api/claims/{claim_id}/steps", operation_id="list_steps")
def list_steps(claim_id: str, db: Database) -> list[Step]:
    """List the steps the agent took on a claim, in order."""
    find_claim(db, claim_id)
    rows = db.execute(
        "SELECT step_id, kind, name, content FROM steps "
        "WHERE claim_id = ? ORDER BY step_id",
        (claim_id,),
    ).fetchall()
    return [Step.model_validate(dict(row)) for row in rows]


@app.post("/api/claims/{claim_id}/decision", operation_id="record_decision")
def record_decision(claim_id: str, decision: Decision, db: Database) -> Claim:
    """Record the decision on a claim in progress."""
    find_claim(db, claim_id)
    over_limit = decision.payout > PAYOUT_LIMIT
    update_claim(
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


@app.post("/api/claims/{claim_id}/payment", operation_id="pay_claim")
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
    update_claim(
        db,
        "UPDATE claims SET paid_amount = ? "
        "WHERE claim_id = ? AND status = 'decided' AND paid_amount IS NULL",
        (payment.amount, claim_id),
        f"Claim {claim_id} is already paid",
    )
    return find_claim(db, claim_id)


@app.post("/api/claims/{claim_id}/sign-off", operation_id="sign_off_claim")
def sign_off_claim(claim_id: str, sign_off: SignOff, db: Database) -> Claim:
    """Sign off an approval over the limit, which pays its payout."""
    find_claim(db, claim_id)
    sql = "SELECT handler_id FROM handlers WHERE handler_id = ?"
    find(db, sql, sign_off.handler_id, "handler")
    update_claim(
        db,
        "UPDATE claims SET status = 'decided', paid_amount = payout, "
        "signed_off_by = ? WHERE claim_id = ? AND status = 'waiting_for_sign_off'",
        (sign_off.handler_id, claim_id),
        f"Claim {claim_id} is not waiting for sign-off",
    )
    return find_claim(db, claim_id)
