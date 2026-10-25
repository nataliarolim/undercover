import { expect, test } from "@playwright/test";

test("the instructions page shows the agent's instructions", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Instructions" }).click();
  const queue = page.getByRole("region", { name: "Running the queue" });
  await expect(queue.getByText(/You are the UnderCover Agent/)).toBeVisible();
  const claim = page.getByRole("region", { name: "Working a claim" });
  await expect(claim.getByText(/You are a claims handler/)).toBeVisible();
  await expect(page.getByText(/Version 2026\.1/)).toHaveCount(0);
});
