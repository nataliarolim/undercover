"""The agent's instructions."""

from pathlib import Path

from fastapi import APIRouter

from backend.models import Instructions
from backend.seed import DATA

INSTRUCTIONS = Path(__file__).parent / "instructions.md"

router = APIRouter()


@router.get("/instructions", operation_id="get_instructions")
def get_instructions() -> Instructions:
    """Get the agent's instructions, followed by the policy wording."""
    instructions = INSTRUCTIONS.read_text(encoding="utf-8")
    wording = (DATA / "policy_wording.md").read_text(encoding="utf-8")
    return Instructions(instructions=f"{instructions}\n{wording}")
