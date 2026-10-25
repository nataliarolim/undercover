import { expect, test } from "@playwright/test";

test("the queue lists every claim with where it stands", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("row")).toHaveCount(26);
  const row = page.getByRole("row", { name: /CLM-1001/ });
  await expect(row.getByText("Waiting", { exact: true })).toBeVisible();
  await row.getByRole("link", { name: "CLM-1001" }).click();
  await expect(page).toHaveURL(/#\/claims\/CLM-1001$/);
});
