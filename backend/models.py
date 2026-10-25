"""What the UnderCover API takes and returns."""

from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BaseModel, Field, model_validator

Status = Literal[
    "waiting", "in_progress", "waiting_for_sign_off", "decided", "left_for_handler"
]
DecisionKind = Literal["approve", "decline", "refer"]
Dollars = Annotated[float, Field(ge=0), AfterValidator(lambda amount: round(amount, 2))]


class ClaimSummary(BaseModel):
    claim_id: str
    summary: str
    claim_type: str
    amount_claimed: float
    status: Status
    decision: DecisionKind | None
    payout: float | None
    attempts: int


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
    error: str | None
    run_id: int | None


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


DocumentName = Literal["policy_wording", "claims_manual"]


class SectionHeading(BaseModel):
    document: DocumentName
    section: int
    title: str
    topics: list[str]


class Section(SectionHeading):
    text: str


class Instructions(BaseModel):
    claim: str


class NewStep(BaseModel):
    kind: Literal["tool_call", "tool_result", "message", "error"]
    name: str
    content: str


class Step(NewStep):
    step_id: int


class Decision(BaseModel):
    decision: DecisionKind
    payout: Dollars
    rationale: str
    policy_section: str

    @model_validator(mode="after")
    def payout_fits_decision(self) -> Self:
        if (self.decision == "approve") != (self.payout > 0):
            raise ValueError(
                "An approval needs a payout above 0, a decline or a referral 0"
            )
        return self


class Payment(BaseModel):
    amount: Dollars


class SignOff(BaseModel):
    handler_id: str


class StartClaim(BaseModel):
    run_id: int


class Failure(BaseModel):
    error: str


class NewRun(BaseModel):
    cap: int = Field(ge=1)


class Todo(BaseModel):
    content: str
    status: Literal["to_do", "in_progress", "done", "left_for_handler"]


class Todos(BaseModel):
    todos: list[Todo]


class Finish(BaseModel):
    summary: str


class Run(BaseModel):
    run_id: int
    cap: int
    status: Literal["running", "finished", "stopped"]
    todos: list[Todo]
    summary: str | None
    started_at: str
    finished_at: str | None
