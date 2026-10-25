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
    Handler,
    Instructions,
    Policy,
)
from backend.seed import DATA, seed

INSTRUCTIONS = Path(__file__).parent / "instructions.md"

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
