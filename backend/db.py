"""The UnderCover database."""

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, status

SCHEMA = """
DROP TABLE IF EXISTS steps;
DROP TABLE IF EXISTS claims;
DROP TABLE IF EXISTS policies;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS handlers;

CREATE TABLE claims (
    claim_id TEXT PRIMARY KEY,
    record TEXT NOT NULL,
    status TEXT NOT NULL,
    decision TEXT,
    payout REAL,
    rationale TEXT,
    policy_section TEXT,
    paid_amount REAL,
    signed_off_by TEXT
);
CREATE TABLE policies (policy_id TEXT PRIMARY KEY, record TEXT NOT NULL);
CREATE TABLE customers (customer_id TEXT PRIMARY KEY, record TEXT NOT NULL);
CREATE TABLE handlers (handler_id TEXT PRIMARY KEY, record TEXT NOT NULL);
CREATE TABLE steps (
    step_id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim_id TEXT NOT NULL REFERENCES claims (claim_id),
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    content TEXT NOT NULL
);
"""


def database_path() -> Path:
    """Return the database file, from UNDERCOVER_DB or the default."""
    return Path(os.getenv("UNDERCOVER_DB", "backend/undercover.db"))


def connect() -> sqlite3.Connection:
    """Open the database, committing each statement as it runs."""
    # FastAPI may run a dependency and its route on different threads.
    connection = sqlite3.connect(
        database_path(), autocommit=True, check_same_thread=False
    )
    connection.row_factory = sqlite3.Row
    return connection


def database() -> Iterator[sqlite3.Connection]:
    """Give a route a connection and close it afterwards."""
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()


Database = Annotated[sqlite3.Connection, Depends(database)]


def find(db: sqlite3.Connection, sql: str, key: object, what: str) -> sqlite3.Row:
    """Return the one row the query finds for key, or a 404."""
    row = db.execute(sql, (key,)).fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"There is no {what} {key}")
    return row


def update(
    db: sqlite3.Connection, sql: str, params: tuple[object, ...], conflict: str
) -> None:
    """Run an update that only applies in the right state, or a 409."""
    if db.execute(sql, params).rowcount == 0:
        raise HTTPException(status.HTTP_409_CONFLICT, conflict)
