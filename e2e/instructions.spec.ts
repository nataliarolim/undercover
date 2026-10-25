import { expect, test } from "@playwright/test";

test("the instructions page shows the agent's instructions", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Instructions" }).click();
  await expect(page.getByText(/You are the UnderCover Agent/)).toBeVisible();
  await expect(page.getByText(/Version 2026\.1/)).toBeVisible();
});
