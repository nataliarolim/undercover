# Status

The pilot is being built from `docs/PLAN.md`. Done so far: Phases 1 to 4.

## Built

- `backend/`: FastAPI on SQLite. `uv run -m backend.seed` resets the database (`backend/undercover.db`, or `UNDERCOVER_DB`) to the records in `data/`, every claim waiting; the backend seeds itself on its first start. Read routes for claims, policies, a customer's claim history (no contact details), handlers and the agent's instructions (`backend/instructions.md` followed by the policy wording).
  The claim workflow: start, steps, decision, payment and sign-off. Claims go waiting, in progress, then decided, or waiting for sign-off when an approval is over the $1,000 limit in `data/company.json`. The payment route never pays over the limit; a handler's sign-off pays those.
- `agent/`: the UnderCover Agent. `run(claim_id, thread_id)` starts the claim, takes its system prompt from the API, and posts every tool call, result and reply as a step. Five tools bound to the claim: `get_claim`, `get_policy`, `get_claim_history`, `record_decision`, `pay_claim`; none signs off. `uv run -m agent` works every waiting claim; `uv run -m agent CLM-1001` works one.
  Not yet run on a real model: a Netskope proxy policy on the build machine blocks OpenRouter chat requests.
- `dashboard/`: React on Vite, in UnderCover's brand, light and dark. Hash routes: `#/` the queue (a count per status and every claim, refreshed every 2 s), `#/instructions` the agent's instructions, read only, and `#/claims/<id>`, a placeholder until Phase 5.
- `e2e/`: the queue and the instructions page. Playwright runs its own backend on port 8001 with `backend/e2e.db`, seeded at start, and Vite on 5174, so `npm run check` never touches the queue `npm run dev` serves.

## Run it

- `npm run dev` starts the backend on port 8000 and the dashboard on 5173
- `uv run -m backend.seed` resets the queue
- `uv run -m agent` works the queue, with `npm run dev` up
- `npm run check` runs every check
