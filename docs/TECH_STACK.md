# Tech stack

- `backend/`: FastAPI and SQLite, with routes split by resource under one `/api` prefix. Every API operation has an `operation_id`, a one-line docstring and no optional inputs. Paying a claim is a separate operation that takes the amount.
- `agent/`: LangChain's `create_agent` and its middleware on OpenRouter, with no other agent framework. `uv run -m agent` works the queue in one run (`--cap N` limits it; naming claims works only those): a queue agent hands each claim to a fresh claim agent. It reaches claims, documents and its instructions only through the backend's API, in `agent/api.py`. Tools are in `agent/tools.py` and the harness in `agent/harness.py`. Thread ids are the run id and `{run_id}-{claim_id}-{attempt}`. It uses `deepseek/deepseek-v4.1-flash` with low reasoning effort by default, or the model in the environment variable `MODEL_NAME` if set, such as `openrouter/free`.
- `dashboard/`: React, Vite and TypeScript.
- `e2e/`: Playwright tests.
- `data/`: the business data the backend starts from. The agent never sees `data/evals/`, which holds the answer key.

Python 3.12 with uv, all in the root `pyproject.toml`. Node 26. The OpenRouter key is `OPENROUTER_API_KEY` in `.env`.
