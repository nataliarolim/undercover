# Code standards

1. Keep it simple, do not overcomplicate.
2. Comments only when necessary.
3. Be concise: a short README and no emojis.
4. IMPORTANT: avoid overly defensive code. Handle exceptions only when necessary.
5. Use uv: ALWAYS `uv run`, NEVER `python3`.
6. TypeScript: strict mode, never `any`.
7. Each app has one module that talks to the backend: `agent/api.py` and `dashboard/src/api.ts`. The base URL and every path are there, and no other module builds a URL. The backend writes `/api` once.
8. Imports point one way. Nothing imports an entry point, and nothing reaches into another module's private names.
9. In the agent, every tool is in `tools.py` and reads run state from `ToolRuntime` context. `harness.py` holds the agent machinery and no UnderCover rules.
10. Agent instructions give a goal and the rules around it, not numbered steps.
