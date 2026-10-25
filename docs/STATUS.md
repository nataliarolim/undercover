# Status

The pilot is being built from `docs/PLAN.md`. Done so far: Phases 1 and 2.

## Built

- `backend/`: FastAPI on SQLite. `uv run -m backend.seed` resets the database (`backend/undercover.db`, or `UNDERCOVER_DB`) to the records in `data/`, every claim waiting; the backend seeds itself on its first start. Read routes for claims, policies, a customer's claim history (no contact details), handlers and the agent's instructions (`backend/instructions.md` followed by the policy wording).
  The claim workflow: start, steps, decision, payment and sign-off. Claims go waiting, in progress, then decided, or waiting for sign-off when an approval is over the $1,000 limit in `data/company.json`. The payment route never pays over the limit; a handler's sign-off pays those.
- `agent/`: still the skeleton's `run(claim_id, thread_id)` with one health tool.
- `dashboard/`: still the skeleton's health page.
- `e2e/`: one test of that page.

## Run it

- `npm run dev` starts the backend on port 8000 and the dashboard on 5173
- `uv run -m backend.seed` resets the queue
- `npm run check` runs every check
