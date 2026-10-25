import { expect, test, type APIRequestContext } from "@playwright/test";

async function startRun(request: APIRequestContext, cap: number) {
  const response = await request.post("/api/runs", { data: { cap } });
  return ((await response.json()) as { run_id: number }).run_id;
}

function todos(first: string) {
  return {
    todos: [
      { content: "Decide CLM-1006", status: first },
      { content: "Decide CLM-1007", status: "to_do" },
    ],
  };
}

test("the queue page shows the run's to-do list filling in", async ({
  page,
  request,
}) => {
  const runId = await startRun(request, 2);
  await page.goto("/");
  const run = page.getByRole("region", { name: "Current run" });
  await expect(run.getByRole("heading")).toHaveText(
    `Run ${String(runId)} Running`,
  );
  await expect(run.getByText("No to-do list yet.")).toBeVisible();

  await request.put(`/api/runs/${String(runId)}/todos`, {
    data: todos("in_progress"),
  });
  const items = run
    .getByRole("list", { name: "To-do list" })
    .getByRole("listitem");
  await expect(items).toHaveText([
    "In progress Decide CLM-1006",
    "To do Decide CLM-1007",
  ]);

  await request.put(`/api/runs/${String(runId)}/todos`, {
    data: todos("done"),
  });
  await expect(items.first()).toHaveText("Done Decide CLM-1006");

  await request.post(`/api/runs/${String(runId)}/finish`, {
    data: { summary: "Two claims decided." },
  });
  await expect(run.getByText("Two claims decided.")).toBeVisible();
  await expect(run.getByRole("heading")).toHaveText(
    `Run ${String(runId)} Finished`,
  );
});

test("a claim that fails twice is left for a handler", async ({
  page,
  request,
}) => {
  const runId = await startRun(request, 1);
  for (const attempt of [1, 2]) {
    await request.post("/api/claims/CLM-1008/start", {
      data: { run_id: runId },
    });
    await request.post("/api/claims/CLM-1008/release", {
      data: { error: `TimeoutError: attempt ${String(attempt)} took too long` },
    });
  }

  await page.goto("/");
  const row = page.getByRole("row", { name: /CLM-1008/ });
  await expect(row.getByText("Left for a handler")).toBeVisible();
  await row.getByRole("link", { name: "CLM-1008" }).click();
  await expect(
    page.getByText(
      "TimeoutError: attempt 2 took too long. Left for a handler after 2 attempts.",
    ),
  ).toBeVisible();
});
