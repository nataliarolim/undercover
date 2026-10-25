import re

import pytest


def test_list_sections(client):
    sections = client.get("/api/documents").json()
    wording = [s for s in sections if s["document"] == "policy_wording"]
    manual = {s["section"]: s for s in sections if s["document"] == "claims_manual"}
    assert len(wording) == 12
    assert len(manual) == 14
    assert manual[7]["title"] == "Interpretation notes"
    assert "Wild animals" in manual[7]["topics"]
    assert "Electronics Plus" in wording[7]["topics"]
    assert "text" not in sections[0]


def test_read_section(client):
    section = client.get("/api/documents/claims_manual/sections/10").json()
    assert section["title"] == "Meals without receipts"
    assert "$35 per traveler" in section["text"]


def test_unknown_section_is_not_found(client):
    response = client.get("/api/documents/policy_wording/sections/99")
    assert response.status_code == 404
    assert response.json()["detail"] == "There is no section 99 in policy_wording"


@pytest.mark.parametrize("document", ["customers", "claims", "policy_wording.md"])
def test_only_the_wording_and_the_manual_can_be_read(client, document):
    assert client.get(f"/api/documents/{document}/sections/1").status_code == 422


def test_claim_instructions_give_a_goal_without_the_wording(client):
    claim = client.get("/api/instructions").json()["claim"]
    assert claim.startswith("You are a claims handler at UnderCover")
    assert "Pay an approval of $1,000.00 or less" in claim
    assert "## 1. Your plan" not in claim
    assert re.search(r"^\d+\.", claim, re.MULTILINE) is None
