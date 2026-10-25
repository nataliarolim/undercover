# Status

The pilot from `docs/PLAN.md` is built. The harness from `docs/PLAN_HARNESS.md` is in progress: Phase 1 is done. Not yet done: the pilot's checks on a real model, because a Netskope proxy policy on the build machine blocks OpenRouter chat requests.

## Built

- `backend/`: FastAPI on SQLite, with routes in `claims.py` and `documents.py` under one `/api` prefix (`backend/undercover.db`, or `UNDERCOVER_DB`), seeded from `data/` on its first start.
  - Reads: claims, policies, a customer's claim history (no contact details), handlers, and the agent's instructions (`backend/instructions.md` followed by the policy wording).
  - Workflow: start, steps, decision, payment, sign-off. Claims go waiting, in progress, then decided, or waiting for sign-off when an approval is over the limit in `data/company.json` ($1,000).
  - The payment route never pays over the limit; a handler's sign-off pays those.
- `agent/`: the UnderCover Agent on `create_agent`, DeepSeek V4.1 Flash at low reasoning effort by default (`MODEL_NAME` overrides).
  - `api.py`: every call to the backend, with its URL in one place. `tools.py`: every tool, reading the claim from `ToolRuntime` context. `harness.py`: the model, building agents, streaming steps. `__main__.py`: the CLI.
  - `run_claim` starts the claim, takes its system prompt from the API, and posts every tool call, result and reply as a step. Five tools: `get_claim`, `get_policy`, `get_claim_history`, `record_decision`, `pay_claim`; none signs off.
- `dashboard/`: React on Vite, in UnderCover's brand, light and dark.
  - `#/`: the queue, with a count per status, refreshed every 2 s.
  - `#/claims/<id>`: the claim in full with its policy and claim history, the decision and its reasons, the agent's steps as they happen, and sign-off.
  - `#/instructions`: the agent's instructions, read only.
- `e2e/`: the queue, the instructions, a claim page, live steps and sign-off. Playwright runs its own backend on port 8001 with `backend/e2e.db`, seeded at start, and Vite on 5174, so `npm run check` never touches the queue `npm run dev` serves.

## Run it

| Command | What it does |
|---|---|
| `npm run dev` | Backend on port 8000, dashboard on http://localhost:5173 |
| `uv run -m agent` | Works every waiting claim, with `npm run dev` up |
| `uv run -m agent CLM-1001` | Works one claim |
| `uv run -m backend.seed` | Resets the queue; a decided claim is final until then |
| `npm run check` | Every check |

## Known limits

- A run that crashes leaves its claim in progress; reseed to reset it.
- With no sign-in, the API can't tell callers apart. The $1,000 block holds against the agent because it has no sign-off tool.
