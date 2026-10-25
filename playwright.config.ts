import { defineConfig } from "@playwright/test";

// The tests write decisions, so they run on their own database and ports,
// never on the queue that `npm run dev` serves. They run one at a time: the
// queue page shows the latest run, and starting a run stops the one before.
export default defineConfig({
  testDir: "e2e",
  workers: 1,
  outputDir: "e2e/test-results",
  reporter: "list",
  use: { baseURL: "http://localhost:5174" },
  webServer: [
    {
      command:
        "uv run -m backend.seed && uv run -m uvicorn backend.main:app --port 8001",
      env: { UNDERCOVER_DB: "backend/e2e.db" },
      url: "http://127.0.0.1:8001/api/health",
      reuseExistingServer: false,
    },
    {
      command: "npx vite dashboard --port 5174 --strictPort",
      env: { API_URL: "http://127.0.0.1:8001" },
      url: "http://localhost:5174",
      reuseExistingServer: false,
    },
  ],
});
