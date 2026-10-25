import { expect, test } from "@playwright/test";

test("a handler signs off an approval over $1,000, which pays it", async ({
  page,
  request,
}) => {
  await request.post("/api/claims/CLM-1003/start");
  await request.post("/api/claims/CLM-1003/decision", {
    data: {
      decision: "approve",
      payout: 3750,
      rationale: "A fall abroad is a sudden injury during the trip.",
      policy_section: "Section 7, Emergency Medical",
    },
  });
  const payment = await request.post("/api/claims/CLM-1003/payment", {
    data: { amount: 3750 },
  });
  expect(payment.status()).toBe(403);

  await page.goto("/#/claims/CLM-1003");
  const heading = page.getByRole("heading", { level: 1 });
  await expect(heading).toHaveText("CLM-1003 Waiting for sign-off");
  await page.getByLabel("Handler").selectOption({ label: "Dana Whitfield" });
  await page
    .getByRole("button", { name: "Sign off and pay $3,750.00" })
    .click();

  await expect(heading).toHaveText("CLM-1003 Decided");
  await expect(
    page.getByText("Paid $3,750.00, signed off by Dana Whitfield"),
  ).toBeVisible();
});
