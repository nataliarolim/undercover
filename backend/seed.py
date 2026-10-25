"""Reset the database to UnderCover's records in data/."""

import json
from contextlib import closing
from pathlib import Path
from typing import Any

from backend.db import SCHEMA, connect

DATA = Path(__file__).parent.parent / "data"


def load(name: str) -> list[dict[str, Any]]:
    """Read one of the JSON files in data/."""
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def seed() -> dict[str, int]:
    """Recreate the tables and load the records, with every claim waiting."""
    claims = load("claims.json")
    tables = {
        "policies": ("policy_id", load("policies.json")),
        "customers": ("customer_id", load("customers.json")),
        "handlers": ("handler_id", load("handlers.json")),
    }
    with closing(connect()) as db:
        db.executescript(SCHEMA)
        db.execute("BEGIN")
        db.executemany(
            "INSERT INTO claims (claim_id, record, status) VALUES (?, ?, 'waiting')",
            [(claim["claim_id"], json.dumps(claim)) for claim in claims],
        )
        for table, (key, records) in tables.items():
            db.executemany(
                f"INSERT INTO {table} VALUES (?, ?)",  # noqa: S608 - table names are fixed above
                [(record[key], json.dumps(record)) for record in records],
            )
        db.execute("COMMIT")
    return {"claims": len(claims)} | {
        table: len(records) for table, (_, records) in tables.items()
    }


if __name__ == "__main__":
    counts = seed()
    print("Seeded " + ", ".join(f"{n} {table}" for table, n in counts.items()))
