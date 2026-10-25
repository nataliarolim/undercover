"""Work the claims queue: uv run -m agent [--cap N], or uv run -m agent CLM-1001."""

import argparse
import sys

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel

from agent import api, harness, tools

QUEUE_STEP_LIMIT = 500


def missed(context: tools.RunContext) -> str | None:
    """Remind the queue agent of claims it can still take, if there are any."""
    waiting = [claim["claim_id"] for claim in api.get_queue(context.run_id)]
    if not waiting:
        return None
    return f"Before you finish: {', '.join(waiting)} can still be taken in this run."


def print_outcome(step: harness.Step) -> None:
    """Print each line work_claim reports back."""
    if step["kind"] == "tool_result" and step["name"] == "work_claim":
        print(step["content"], flush=True)


def work_queue(
    cap: int | None, queue_llm: BaseChatModel, claim_llm: BaseChatModel
) -> str:
    """Run the queue agent once over the queue, and return its summary."""
    run_id = api.start_run(cap or len(api.list_claims()))["run_id"]
    agent = harness.create(
        queue_llm,
        tools.QUEUE_TOOLS,
        api.get_instructions()["queue"],
        tools.RunContext,
        [tools.REFUSALS, harness.finish_check(missed)],
    )
    summary = harness.run(
        agent,
        "Work the queue.",
        tools.RunContext(run_id, claim_llm),
        harness.config(str(run_id), QUEUE_STEP_LIMIT),
        print_outcome,
    )
    api.finish_run(run_id, summary)
    return summary


def work_claims(claim_ids: list[str], llm: BaseChatModel) -> None:
    """Work the named claims once each, without the queue agent."""
    run_id = api.start_run(len(claim_ids))["run_id"]
    lines = []
    for claim_id in claim_ids:
        try:
            lines.append(tools.work(run_id, claim_id, llm))
        except api.Refused as refused:
            lines.append(f"{claim_id} not started: {refused}")
        print(lines[-1], flush=True)
    api.finish_run(run_id, "\n".join(lines))


def main(argv: list[str]) -> None:
    """Work the whole queue in one run, at most --cap claims, or the named claims."""
    parser = argparse.ArgumentParser(prog="uv run -m agent")
    parser.add_argument("claim_ids", nargs="*", help="work only these claims")
    parser.add_argument("--cap", type=int, help="take at most this many claims")
    args = parser.parse_args(argv)
    load_dotenv(override=True)
    llm = harness.model()
    if args.claim_ids:
        work_claims(args.claim_ids, llm)
    else:
        print(work_queue(args.cap, llm, llm))


if __name__ == "__main__":
    main(sys.argv[1:])
