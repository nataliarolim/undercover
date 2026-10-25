"""The UnderCover database."""

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path

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
