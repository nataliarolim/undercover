import { expect, test } from "@playwright/test";

test("a claim page shows the claim in full", async ({ page }) => {
  await page.goto("/#/claims/CLM-1001");
  await expect(page.getByText(/^My flight home from Rome/)).toBeVisible();
  const items = page.getByRole("region", { name: "Items claimed" });
  await expect(items.getByRole("row")).toHaveCount(4);
  const documents = page.getByRole("region", { name: "Documents" });
  await expect(documents.getByRole("article")).toHaveCount(4);
  const policy = page.getByRole("region", { name: "Policy" });
  await expect(policy.getByText("Premium")).toBeVisible();
  const history = page.getByRole("region", { name: "Claim history" });
  await expect(history.getByRole("listitem")).toHaveCount(1);
  await expect(history.getByText("CLM-0412")).toBeVisible();
});
