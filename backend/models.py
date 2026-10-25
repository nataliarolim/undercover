"""What the UnderCover API takes and returns."""

from typing import Literal

from pydantic import BaseModel

Status = Literal["waiting", "in_progress", "waiting_for_sign_off", "decided"]
DecisionKind = Literal["approve", "decline", "refer"]


class ClaimSummary(BaseModel):
    claim_id: str
    summary: str
    claim_type: str
    amount_claimed: float
    status: Status
    decision: DecisionKind | None
    payout: float | None


class Item(BaseModel):
    description: str
    category: str
    amount: float


class Document(BaseModel):
    name: str
    type: str
    content: str


class Claim(ClaimSummary):
    policy_id: str
    customer_id: str
    submitted_on: str
    incident_date: str
    incident_location: str
    story: str
    items: list[Item]
    documents: list[Document]
    rationale: str | None
    policy_section: str | None
    paid_amount: float | None
    signed_off_by: str | None


class Trip(BaseModel):
    destination: str
    departs_on: str
    returns_on: str
    trip_cost: float


class Policy(BaseModel):
    policy_id: str
    customer_id: str
    plan: str
    add_ons: list[str]
    purchased_on: str
    sold_through: str
    trip: Trip
    travelers: list[str]
    status: str


class PreviousClaim(BaseModel):
    claim_id: str
    filed_on: str
    incident_date: str
    claim_type: str
    summary: str
    outcome: str
    amount_paid: float


class ClaimHistory(BaseModel):
    customer_id: str
    name: str
    customer_since: str
    previous_claims: list[PreviousClaim]


class Handler(BaseModel):
    handler_id: str
    name: str
    role: str


class Instructions(BaseModel):
    instructions: str
