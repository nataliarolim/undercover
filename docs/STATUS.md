# Status

The pilot from `docs/PLAN.md` and the harness from `docs/PLAN_HARNESS.md` are built. Reseed after pulling the harness (`uv run -m backend.seed`): the database schema changed. Not yet done: every check on a real model (the pilot's, and the harness's five-claim trial), because a Netskope proxy policy on the build machine blocks OpenRouter chat requests.

## Built

- `backend/`: FastAPI on SQLite, with routes in `claims.py`, `documents.py` and `runs.py` under one `/api` prefix (`backend/undercover.db`, or `UNDERCOVER_DB`), seeded from `data/` on its first start.
  - Reads: claims, policies, a customer's claim history (no contact details), handlers, and the agent's instructions (`backend/instructions/`, with the payout limit filled in).
  - Documents: the policy wording and the claims manual, listed and read one section at a time. Only those two files can be read.
  - Runs: a run has a cap, a to-do list and a summary. A claim starts only in a running run, within its cap. Starting a run stops the one before and releases its claims in progress.
  - Workflow: start, steps, decision, payment, sign-off, release. Claims go waiting, in progress, then decided, or waiting for sign-off when an approval is over the limit in `data/company.json` ($1,000). A released claim goes back to waiting, or to left for a handler on its second attempt.
  - The payment route never pays over the limit; a handler's sign-off pays those.
- `agent/`: the UnderCover Agent on `create_agent`, DeepSeek V4.1 Flash at low reasoning effort by default (`MODEL_NAME` overrides).
  - `api.py`: every call to the backend, with its URL in one place. `tools.py`: every tool, reading the claim from `ToolRuntime` context. `harness.py`: the model, building agents, streaming steps. `__main__.py`: the CLI.
  - The queue agent works the queue in one run: it keeps a to-do list (`write_todos`), chooses the order (`get_queue`) and hands each claim to `work_claim`, then ends with a summary for the handlers. Before it finishes, a finish check reminds it, at most twice, of claims it can still take.
  - `work_claim` starts the claim and has a fresh claim agent decide it, posting every tool call, result and reply as a step on the claim. Whatever ends the claim agent (an error, its 50-step limit, no decision), a claim left in progress is released. It reports one line from the claim's record.
  - The claim agent's seven tools: `get_claim`, `get_policy`, `get_claim_history`, `list_sections`, `read_section`, `record_decision`, `pay_claim`; none signs off.
- `dashboard/`: React on Vite, in UnderCover's brand, light and dark.
  - `#/`: the queue, with a count per status, and the current run: its status, cap, to-do list and, once finished, its summary. Refreshed every 2 s.
  - `#/claims/<id>`: the claim in full with its policy and claim history, the decision and its reasons, the sections the agent read, its steps as they happen, any failed attempts, and sign-off.
  - `#/instructions`: the agent's instructions, read only.
- `e2e/`: the queue, the instructions, a claim page, live steps, sign-off, a run's to-do list and a claim left for a handler. The specs run one at a time. Playwright runs its own backend on port 8001 with `backend/e2e.db`, seeded at start, and Vite on 5174, so `npm run check` never touches the queue `npm run dev` serves.

## Run it

| Command | What it does |
|---|---|
| `npm run dev` | Backend on port 8000, dashboard on http://localhost:5173 |
| `uv run -m agent` | One run of the queue agent over the whole queue, with `npm run dev` up |
| `uv run -m agent --cap 5` | One run that takes at most five claims; the rest stay waiting |
| `uv run -m agent CLM-1001` | Works the named claims once each, without the queue agent |
| `uv run -m backend.seed` | Resets the queue; a decided claim is final until then |
| `npm run check` | Every check |

Behind a proxy that inspects TLS, point `SSL_CERT_FILE` at the proxy's certificate bundle when you run the agent, so Python trusts it.

## Known limits

- With no sign-in, the API can't tell callers apart. The $1,000 block holds against the agent because it has no sign-off tool.
- One run at a time: starting a run stops the one before and releases its claims. A run whose process was killed shows Running until the next run starts.
- A claim decided but whose payment failed stays decided and unpaid; it is never retried.
- A claim left for a handler can't yet be decided in the dashboard; reseed to reset it.
