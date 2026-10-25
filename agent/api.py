"""The UnderCover backend's API, the agent's only way to reach the backend."""

from typing import Any

import httpx

BACKEND_URL = "http://localhost:8000/api"


class Refused(Exception):
    """The backend refused a request (a 4xx); the message is its reply."""


def client() -> httpx.Client:
    """Return a client for the backend."""
    return httpx.Client(base_url=BACKEND_URL, timeout=10)


def call(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    """Call the backend, raising Refused for a 4xx and an error for a 5xx."""
    with client() as backend:
        response = backend.request(method, path, json=body)
    if response.is_client_error:
        raise Refused(response.text)
    return response.raise_for_status().json()


def list_claims() -> list[dict[str, Any]]:
    """List the claims queue."""
    return call("GET", "/claims")


def get_claim(claim_id: str) -> dict[str, Any]:
    """Get a claim in full."""
    return call("GET", f"/claims/{claim_id}")


def get_policy(policy_id: str) -> dict[str, Any]:
    """Get a policy."""
    return call("GET", f"/policies/{policy_id}")


def get_claim_history(customer_id: str) -> dict[str, Any]:
    """Get a customer's earlier claims."""
    return call("GET", f"/customers/{customer_id}/history")


def list_sections() -> list[dict[str, Any]]:
    """List the sections of the policy wording and the claims manual."""
    return call("GET", "/documents")


def read_section(document: str, section: int) -> dict[str, Any]:
    """Read one section of the policy wording or the claims manual."""
    return call("GET", f"/documents/{document}/sections/{section}")


def get_instructions() -> dict[str, str]:
    """Get the agent's instructions."""
    return call("GET", "/instructions")


def start_run(cap: int) -> dict[str, Any]:
    """Start a run that takes at most cap claims."""
    return call("POST", "/runs", {"cap": cap})


def get_queue(run_id: int) -> list[dict[str, Any]]:
    """List the waiting claims a run can still take."""
    return call("GET", f"/runs/{run_id}/queue")


def update_todos(run_id: int, todos: list[Any]) -> dict[str, Any]:
    """Replace a run's to-do list."""
    return call("PUT", f"/runs/{run_id}/todos", {"todos": todos})


def finish_run(run_id: int, summary: str) -> dict[str, Any]:
    """Finish a run with its summary for the handlers."""
    return call("POST", f"/runs/{run_id}/finish", {"summary": summary})


def start_claim(claim_id: str, run_id: int) -> dict[str, Any]:
    """Start a waiting claim in a run."""
    return call("POST", f"/claims/{claim_id}/start", {"run_id": run_id})


def add_step(claim_id: str, step: dict[str, str]) -> dict[str, Any]:
    """Record a step the agent took on a claim."""
    return call("POST", f"/claims/{claim_id}/steps", step)


def record_decision(claim_id: str, decision: dict[str, Any]) -> dict[str, Any]:
    """Record the decision on a claim."""
    return call("POST", f"/claims/{claim_id}/decision", decision)


def release_claim(claim_id: str, error: str) -> dict[str, Any]:
    """Release a claim that failed in progress."""
    return call("POST", f"/claims/{claim_id}/release", {"error": error})


def pay_claim(claim_id: str, amount: float) -> dict[str, Any]:
    """Pay an approved claim its payout."""
    return call("POST", f"/claims/{claim_id}/payment", {"amount": amount})
