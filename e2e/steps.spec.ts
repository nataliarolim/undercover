import { expect, test } from "@playwright/test";

test("the agent's steps appear while it works", async ({ page, request }) => {
  await page.goto("/#/claims/CLM-1002");
  await expect(page.getByText("No steps yet.")).toBeVisible();

  await request.post("/api/claims/CLM-1002/start");
  await request.post("/api/claims/CLM-1002/steps", {
    data: { kind: "tool_call", name: "get_claim", content: "{}" },
  });

  await expect(
    page.getByText("The agent is working on this claim."),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Agent steps" }).getByText("get_claim"),
  ).toBeVisible();
});
