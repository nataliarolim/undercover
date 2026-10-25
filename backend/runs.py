"""Runs of the agent over the queue: their cap, to-do list and summary."""

import json
import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter

from backend.claims import load_claim, release_in_progress
from backend.db import Database, find, update
from backend.models import ClaimSummary, Finish, NewRun, Run, Todos

router = APIRouter()


def now() -> str:
    """The time now, such as 2026-10-25T12:00:00+00:00."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def load_run(row: sqlite3.Row) -> Run:
    """Read a run with its to-do list."""
    return Run.model_validate(dict(row) | {"todos": json.loads(row["todos"])})


def find_run(db: sqlite3.Connection, run_id: int) -> Run:
    """Return the run, or a 404."""
    return load_run(find(db, "SELECT * FROM runs WHERE run_id = ?", run_id, "run"))


@router.post("/runs", operation_id="start_run")
def start_run(new: NewRun, db: Database) -> Run:
    """Start a run, stopping any run still running and releasing its claims."""
    db.execute(
        "UPDATE runs SET status = 'stopped', finished_at = ? WHERE status = 'running'",
        (now(),),
    )
    for (claim_id,) in db.execute(
        "SELECT claim_id FROM claims WHERE status = 'in_progress'"
    ).fetchall():
        release_in_progress(
            db, claim_id, "The run stopped before the claim was decided"
        )
    ((run_id,),) = db.execute(
        "INSERT INTO runs (cap, status, started_at) VALUES (?, 'running', ?) "
        "RETURNING run_id",
        (new.cap, now()),
    ).fetchall()
    return find_run(db, run_id)


@router.get("/runs/latest", operation_id="get_latest_run")
def get_latest_run(db: Database) -> Run | None:
    """Get the latest run with its to-do list, or null before the first run."""
    row = db.execute("SELECT * FROM runs ORDER BY run_id DESC LIMIT 1").fetchone()
    return None if row is None else load_run(row)


@router.get("/runs/{run_id}/queue", operation_id="get_queue")
def get_queue(run_id: int, db: Database) -> list[ClaimSummary]:
    """List the waiting claims a run may still take: any until it holds its cap."""
    run = find_run(db, run_id)
    if run.status != "running":
        return []
    rows = db.execute(
        "SELECT * FROM claims WHERE status = 'waiting' AND (run_id IS :run OR "
        "(SELECT COUNT(*) FROM claims WHERE run_id = :run) < :cap) ORDER BY claim_id",
        {"run": run_id, "cap": run.cap},
    ).fetchall()
    return [load_claim(row) for row in rows]


@router.put("/runs/{run_id}/todos", operation_id="update_todos")
def update_todos(run_id: int, todos: Todos, db: Database) -> Run:
    """Replace a running run's to-do list."""
    find_run(db, run_id)
    update(
        db,
        "UPDATE runs SET todos = ? WHERE run_id = ? AND status = 'running'",
        (json.dumps([todo.model_dump() for todo in todos.todos]), run_id),
        f"Run {run_id} is not running",
    )
    return find_run(db, run_id)


@router.post("/runs/{run_id}/finish", operation_id="finish_run")
def finish_run(run_id: int, finish: Finish, db: Database) -> Run:
    """Finish a running run with its summary for the handlers."""
    find_run(db, run_id)
    update(
        db,
        "UPDATE runs SET status = 'finished', summary = ?, finished_at = ? "
        "WHERE run_id = ? AND status = 'running'",
        (finish.summary, now(), run_id),
        f"Run {run_id} is not running",
    )
    return find_run(db, run_id)
