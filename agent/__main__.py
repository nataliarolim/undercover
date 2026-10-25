"""Work the claims queue: uv run -m agent, or uv run -m agent CLM-1001 for one claim."""

import sys
import uuid
from typing import Any

from dotenv import load_dotenv

from agent import api, harness, tools


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
    load_dotenv(override=True)
    llm = harness.model()
    waiting = [c["claim_id"] for c in api.list_claims() if c["status"] == "waiting"]
    chosen = claim_ids or waiting
    run_id = api.start_run(len(chosen))["run_id"]
    lines = []
    for claim_id in chosen:
        tools.run_claim(claim_id, run_id, str(uuid.uuid4()), llm)
        lines.append(outcome(api.get_claim(claim_id)))
        print(lines[-1], flush=True)
    api.finish_run(run_id, "\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1:])
