"""The policy wording and the claims manual by section, and the agent's instructions."""

import re
from itertools import batched
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from backend.claims import PAYOUT_LIMIT, dollars
from backend.models import DocumentName, Instructions, Section, SectionHeading
from backend.seed import DATA

INSTRUCTIONS = Path(__file__).parent / "instructions"
DOCUMENTS: dict[DocumentName, Path] = {
    "policy_wording": DATA / "policy_wording.md",
    "claims_manual": DATA / "claims_manual.md",
}
HEADING = re.compile(r"^## (\d+)\. (.+)$", re.MULTILINE)
TOPIC = re.compile(r"^\*\*(.+?)\.\*\*", re.MULTILINE)

router = APIRouter()


def sections(document: DocumentName) -> list[Section]:
    """Split a document at its numbered headings, with each section's bold topics."""
    text = DOCUMENTS[document].read_text(encoding="utf-8")
    return [
        Section(
            document=document,
            section=int(number),
            title=title,
            topics=TOPIC.findall(body),
            text=body.strip(),
        )
        for number, title, body in batched(HEADING.split(text)[1:], 3)
    ]


def instructions(name: str) -> str:
    """Read one of the agent's instructions, with the payout limit filled in."""
    text = (INSTRUCTIONS / f"{name}.md").read_text(encoding="utf-8")
    return text.replace("{payout_limit}", dollars(PAYOUT_LIMIT))


@router.get("/documents", operation_id="list_sections")
def list_sections() -> list[SectionHeading]:
    """List the sections of the policy wording and the claims manual, without text."""
    return [section for document in DOCUMENTS for section in sections(document)]


@router.get("/documents/{document}/sections/{section}", operation_id="read_section")
def read_section(document: DocumentName, section: int) -> Section:
    """Read one section of the policy wording or the claims manual."""
    for found in sections(document):
        if found.section == section:
            return found
    raise HTTPException(
        status.HTTP_404_NOT_FOUND, f"There is no section {section} in {document}"
    )


@router.get("/instructions", operation_id="get_instructions")
def get_instructions() -> Instructions:
    """Get the agent's instructions for working a claim."""
    return Instructions(claim=instructions("claim"))
