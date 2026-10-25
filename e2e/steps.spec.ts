import { expect, test } from "@playwright/test";

test("the agent's steps appear while it works", async ({ page, request }) => {
  await page.goto("/#/claims/CLM-1002");
  await expect(page.getByText("No steps yet.")).toBeVisible();

  const run = await request.post("/api/runs", { data: { cap: 1 } });
  const { run_id } = (await run.json()) as { run_id: number };
  await request.post("/api/claims/CLM-1002/start", { data: { run_id } });
  await request.post("/api/claims/CLM-1002/steps", {
    data: { kind: "tool_call", name: "get_claim", content: "{}" },
  });
  const section = await request.get("/api/documents/claims_manual/sections/7");
  await request.post("/api/claims/CLM-1002/steps", {
    data: {
      kind: "tool_result",
      name: "read_section",
      content: await section.text(),
    },
  });

  await expect(
    page.getByText("The agent is working on this claim."),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Agent steps" }).getByText("get_claim"),
  ).toBeVisible();
  await expect(
    page
      .getByRole("region", { name: "What the agent read" })
      .getByText("Claims manual, 7. Interpretation notes"),
  ).toBeVisible();
});
