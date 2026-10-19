# Plan: the claims pilot

The pilot builds what `docs/SPEC.md` asks for: a backend that holds the queue and enforces the rules, the UnderCover Agent that decides claims through the backend's API, and a dashboard where the handlers watch the queue, read each decision, follow the agent step by step, read its instructions and sign off large payouts.

## The approach

- **The backend is the source of truth and the referee.** Every rule in the spec that the system "must" enforce lives in the backend, not in the agent's prompt. The $1,000 sign-off rule is checked in the payment operation itself, so a payment over the limit is refused until a handler signs off, whatever the agent does.
- **SQLite with the standard library's `sqlite3`.** One file, `backend/undercover.db`, created on startup from `data/` when it doesn't exist, and rebuilt with `uv run -m backend.seed`. The path comes from `UNDERCOVER_DB` so tests and the end-to-end run each use their own database. Policies, customers and plans are stored as JSON, since the pilot only reads them; claims, steps, decisions and payments get their own columns, since they change.
- **`data/evals/` is never read.** Seeding loads named files from `data/` and nothing under `data/evals/` or `data/security/`. A test checks that seeding never opens those folders.
- **The agent sees only what a handler needs.** It gets the claim, the policy with its plan's limits, the customer's claim history (without contact details or date of birth) and the policy wording. The claims manual stays out, as the spec says.
- **The agent's instructions live in the backend** in `backend/agent_instructions.md`. The agent fetches them through the API at the start of each run, and the dashboard shows the same text read only.
- **Steps are recorded by the agent's runner, not by the model.** `run()` streams the agent and posts each model turn and tool call to the backend as a step, so the record can't be skipped or invented by the model. The dashboard polls a claim's steps while the agent is working.
- **The agent decides, then pays.** It records its decision (approve, decline or refer, the payout, two or three sentences of reasons and the policy section), then calls the payment operation with the amount when it approves. At or under $1,000 the payment goes through and the claim is decided. Over $1,000 the payment is refused and the claim waits for sign-off; when a handler signs off in the dashboard, the backend records the payment and the claim is decided. Nothing is really paid: a payment is a row in the database.

## Claim states

| State | Label on screen | Set when |
|---|---|---|
| `waiting` | Waiting | Seeded (the data's `open`) |
| `in_progress` | In progress | The agent starts the claim |
| `awaiting_signoff` | Waiting for sign-off | The agent approves a payout over $1,000 |
| `decided` | Decided | A decline, a refer, a paid approval, or a sign-off |

## The API

Every operation has an `operation_id`, a one-line docstring and no optional inputs.

| Operation | Route | Used by |
|---|---|---|
| `health` | `GET /api/health` | dashboard |
| `list_claims` | `GET /api/claims` | dashboard |
| `get_claim` | `GET /api/claims/{claim_id}` | agent, dashboard |
| `get_policy` | `GET /api/policies/{policy_id}` | agent, dashboard |
| `get_claim_history` | `GET /api/customers/{customer_id}/claim-history` | agent, dashboard |
| `get_policy_wording` | `GET /api/policy-wording` | agent |
| `get_agent_instructions` | `GET /api/agent/instructions` | agent, dashboard |
| `list_handlers` | `GET /api/handlers` | dashboard |
| `start_claim` | `POST /api/claims/{claim_id}/start` | agent runner |
| `add_step` | `POST /api/claims/{claim_id}/steps` | agent runner |
| `list_steps` | `GET /api/claims/{claim_id}/steps` | dashboard |
| `record_decision` | `POST /api/claims/{claim_id}/decision` | agent |
| `pay_claim` | `POST /api/claims/{claim_id}/payment` | agent |
| `sign_off` | `POST /api/claims/{claim_id}/sign-off` | dashboard |
| `run_agent` | `POST /api/claims/{claim_id}/run` | dashboard |

`run_agent` starts the agent on the claim in a background task, so a handler can start a claim from the dashboard and watch it work.

## Phase 1: Data and the read API

Build the SQLite schema, seeding from `data/`, and the read operations: `list_claims`, `get_claim`, `get_policy` (with its plan's limits and the add-ons), `get_claim_history`, `get_policy_wording`, `get_agent_instructions` and `list_handlers`. Write a first version of `backend/agent_instructions.md`. Add `backend/undercover.db` to `.gitignore`.

- [ ] `uv run -m backend.seed` creates `backend/undercover.db` and prints that it loaded 25 claims, 50 policies, 49 customers and 3 handlers
- [ ] `GET /api/claims` returns 25 claims, each with its id, type, customer name, amount claimed and state `waiting`
- [ ] `GET /api/claims/CLM-1001` returns the story, items and documents, with no decision
- [ ] `GET /api/policies/POL-2001` returns the Premium plan's limits and deductible alongside the policy
- [ ] `GET /api/customers/CUS-3001/claim-history` returns CLM-0412 and no email, phone, address or date of birth
- [ ] `GET /api/claims/CLM-9999` returns 404
- [ ] A test checks that the database holds exactly the claims in `data/claims.json`, and that seeding opens no file under `data/evals/` or `data/security/`
- [ ] A test checks that every route has an `operation_id`, a one-line docstring and no optional inputs, by reading the app's OpenAPI schema
- [ ] `npm run check:python` passes with coverage of at least 80%

## Phase 2: The claim workflow and the payment rule

Build `start_claim`, `add_step`, `list_steps`, `record_decision`, `pay_claim` and `sign_off`, with the state changes in the table above.

- `record_decision` takes the decision, the payout, the reasons and the policy section. It requires a payout above zero for an approval and zero otherwise, and a claim that is in progress.
- `pay_claim` takes the amount. It refuses with 409 unless the claim is approved, the amount equals the approved payout and the claim hasn't been paid. Over $1,000, it refuses with 409 and the message "Payouts over $1,000.00 need a handler's sign-off" until a handler has signed off. The limit comes from `data/company.json`.
- `sign_off` takes a handler id, checks that the handler may approve over the limit, records the sign-off and the payment, and marks the claim decided.

- [ ] Tests cover each state change in the table, through the API
- [ ] A test approves a $1,250.00 payout, then calls `pay_claim` with $1,250.00 and gets 409 with the sign-off message, and the claim has no payment
- [ ] After `sign_off` with HND-01, the same claim is `decided` with one payment of $1,250.00, and a second `pay_claim` gets 409
- [ ] A test approves $400.00, pays $400.00 and the claim is `decided` with one payment; paying a different amount gets 409
- [ ] Decline and refer go straight to `decided` with no payment, and `pay_claim` on them gets 409
- [ ] `record_decision` on a claim that isn't in progress gets 409
- [ ] Steps come back from `list_steps` in the order they were added
- [ ] `npm run check:python` passes

## Phase 3: The UnderCover Agent

Replace the hello-world agent. `run(claim_id, thread_id)` starts the claim, fetches the instructions from the API, and runs `create_agent` with the tools `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `record_decision` and `pay_claim`, each a thin call to the backend. It streams the agent and posts each step. The instructions tell the agent to read everything first, follow the policy wording, work out the payout as section 10 of the wording describes, explain the decision in two or three sentences, name the section, and pay when it approves. The model stays `openai/gpt-6-luna` with low reasoning effort, or `MODEL_NAME` if set.

Add `uv run -m agent CLM-1001` to run one claim, and `uv run -m agent` to work every waiting claim in the queue.

- [ ] A stub-model test runs a claim end to end against the backend: the claim ends `decided` with the stub's decision, reasons and section, and its steps include each tool call in order
- [ ] A stub-model test where the agent approves $1,250.00 and calls `pay_claim` leaves the claim `awaiting_signoff` with no payment, and the agent's tool result carries the refusal
- [ ] A test checks that the instructions the agent uses are the ones the API returns
- [ ] The existing `model()` test still passes for the default model and for `MODEL_NAME`
- [ ] Live, with `OPENROUTER_API_KEY` set: `uv run -m agent CLM-1001` records a decision with reasons and a policy section, and the claim's steps show each tool call (a few cents of API spend)
- [ ] Live: running the agent on a claim it approves for more than $1,000 leaves it `awaiting_signoff` with no payment
- [ ] `npm run check:python` passes

## Phase 4: The dashboard

Build three pages in React with hash routing, so no router library is needed:

- **Queue** (`#/`): every claim with its id, customer, type, amount claimed and a state chip. The four states use Sea Green, Marigold, Coral and Cerulean, darkened for text in light mode, as `docs/BRAND.md` asks. A count of each state sits above the table.
- **Claim** (`#/claims/CLM-1001`): the story, the items, the documents, the policy and plan, and the claim history; then the agent's decision, payout, reasons and section once there is one, and the payment.
- **Agent instructions** (`#/instructions`): the instructions, read only.

Instrument Sans, Instrument Serif and JetBrains Mono from Google Fonts, the brand surfaces in light and dark mode, rounded panels with no outlines, and amounts as $1,250.00. A small typed API module wraps `fetch`, with types for every response.

- [ ] Vitest tests cover each page with a stubbed `fetch`, including each state chip's label and the money format
- [ ] `npm run check:ts` passes with coverage of at least 80%
- [ ] In the browser with the Playwright MCP server: the queue shows 25 claims in the Waiting state
- [ ] In the browser: CLM-1001's page shows its story, three items, documents and Maya Patel's earlier claim
- [ ] In the browser: the instructions page shows the same text as `backend/agent_instructions.md`
- [ ] In the browser: the pages follow the brand in light and dark mode (checked by screenshot)

## Phase 5: Watching the agent, and sign-off

Add the `run_agent` operation and, on the claim page, a "Run the agent" button for a waiting claim. While a claim is in progress, the page polls `list_steps` every second and shows each step as it arrives: what the agent read, what it decided, and what the backend said back. For a claim waiting for sign-off, the page shows the payout and a sign-off form where the handler picks their name; signing off records the payment and the page shows the claim decided.

- [ ] A backend test checks that `run_agent` starts the agent in the background, with the agent's `run` stubbed
- [ ] Vitest tests cover the step list, the polling stopping once the claim leaves `in_progress`, and the sign-off form
- [ ] `npm run check` passes
- [ ] In the browser, live: pressing "Run the agent" on CLM-1001 shows the steps appearing one by one, then the decision and reasons
- [ ] In the browser, live: a claim approved for more than $1,000 shows "Waiting for sign-off" with no payment; signing off as Dana Whitfield shows it decided with the payment

## Phase 6: End-to-end tests, docs and a run through the queue

Playwright starts its own backend on port 8001 with a fresh database in `e2e/`, set through the `webServer` `env` option so it works on Windows, and its own dashboard on port 5174 that proxies to it. The tests drive the workflow through the API in place of the agent, so they never call a model.

- [ ] An end-to-end test: the queue shows 25 waiting claims, and opening one shows its story
- [ ] An end-to-end test: a claim given a decision through the API shows the decision, reasons and section on its page, and its steps
- [ ] An end-to-end test: a claim approved for more than $1,000 shows "Waiting for sign-off"; signing off in the page shows it decided with the payment
- [ ] An end-to-end test: the instructions page shows the instructions
- [ ] `docs/STATUS.md` says what's built and how to run it: `npm run dev`, `uv run -m backend.seed`, `uv run -m agent`
- [ ] Live: `uv run -m agent` works the whole queue, and every claim ends `decided` or `awaiting_signoff`, with no claim over $1,000 paid without a sign-off (about 25 runs of the model, well under a dollar)
- [ ] `npm run check` passes, and the results are reported

## Not in the pilot

As the spec says: no claims manual, no sign-in, no real payments and no messages to customers. Scoring the agent against `data/evals/` is for later, so the pilot never opens it.
