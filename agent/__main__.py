"""Work the claims queue: uv run -m agent, or uv run -m agent CLM-1001 for one claim."""

import sys
import uuid
from typing import Any

import agent.main


def waiting_claims() -> list[str]:
    """Return the ids of the claims waiting in the queue."""
    with agent.main.backend() as client:
        claims = client.get("/api/claims").raise_for_status().json()
    return [claim["claim_id"] for claim in claims if claim["status"] == "waiting"]


def outcome(claim: dict[str, Any]) -> str:
    """Describe where a claim stands after a run, in one line."""
    if claim["decision"] is None:
        return f"{claim['claim_id']} {claim['status']} with no decision"
    return (
        f"{claim['claim_id']} {claim['status']} {claim['decision']} "
        f"${claim['payout']:,.2f}"
    )


def main(claim_ids: list[str]) -> None:
    """Run the agent on the named claims, or on every waiting claim."""
    for claim_id in claim_ids or waiting_claims():
        agent.main.run(claim_id, str(uuid.uuid4()))
        with agent.main.backend() as client:
            claim = client.get(f"/api/claims/{claim_id}").raise_for_status().json()
        print(outcome(claim), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
