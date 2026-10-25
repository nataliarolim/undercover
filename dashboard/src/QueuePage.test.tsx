import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { QueuePage } from "./QueuePage";
import { HELD, RUN, WAITING, stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function row(claimId: string) {
  return within(screen.getByRole("row", { name: new RegExp(claimId) }));
}

it("lists the claims with where each one stands", async () => {
  stubApi({ "/api/claims": [WAITING, HELD], "/api/runs/latest": null });
  render(<QueuePage />);

  expect(await screen.findByRole("link", { name: "CLM-1001" })).toBeDefined();
  expect(row("CLM-1001").getByText("Waiting")).toBeDefined();
  expect(row("CLM-1001").getByText("Trip delay")).toBeDefined();
  expect(row("CLM-1001").getByText("$420.00")).toBeDefined();
  expect(row("CLM-1003").getByText("Waiting for sign-off")).toBeDefined();
  expect(row("CLM-1003").getByText("Approve")).toBeDefined();
  expect(row("CLM-1003").getByText("$3,750.00")).toBeDefined();
});

it("counts the claims in each status", async () => {
  stubApi({
    "/api/claims": [WAITING, HELD, { ...WAITING, claim_id: "CLM-1002" }],
  });
  render(<QueuePage />);

  const tiles = within(
    await screen.findByRole("list", { name: "Claims by status" }),
  );
  const counts = tiles.getAllByRole("listitem").map((tile) => tile.textContent);
  expect(counts).toEqual([
    "Waiting2",
    "In progress0",
    "Waiting for sign-off1",
    "Decided0",
    "Left for a handler0",
  ]);
});

it("refreshes the queue every two seconds", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  stubApi({ "/api/claims": [WAITING] });
  render(<QueuePage />);
  expect(await screen.findByRole("link", { name: "CLM-1001" })).toBeDefined();

  stubApi({ "/api/claims": [{ ...WAITING, status: "in_progress" }] });
  await vi.advanceTimersByTimeAsync(2000);
  expect(await row("CLM-1001").findByText("In progress")).toBeDefined();
});

it("shows the current run's to-do list as it fills in", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  stubApi({ "/api/claims": [WAITING], "/api/runs/latest": RUN });
  render(<QueuePage />);

  const list = within(await screen.findByRole("list", { name: "To-do list" }));
  const items = list.getAllByRole("listitem").map((item) => item.textContent);
  expect(items).toEqual([
    "Done Decide CLM-1001",
    "In progress Decide CLM-1002",
    "To do Decide CLM-1003",
    "Left for a handler Decide CLM-1004",
  ]);
  const run = within(screen.getByRole("region", { name: "Current run" }));
  expect(run.getByText("Running")).toBeDefined();
  expect(run.getByText("Takes at most 5 claims.")).toBeDefined();

  stubApi({
    "/api/claims": [WAITING],
    "/api/runs/latest": {
      ...RUN,
      status: "finished",
      summary: "Three claims decided; one left for a handler.",
    },
  });
  await vi.advanceTimersByTimeAsync(2000);
  expect(await run.findByText("Finished")).toBeDefined();
  expect(
    run.getByText("Three claims decided; one left for a handler."),
  ).toBeDefined();
});

it("says when there are no runs or no to-do list yet", async () => {
  stubApi({ "/api/claims": [WAITING], "/api/runs/latest": null });
  render(<QueuePage />);
  expect(await screen.findByText("No runs yet.")).toBeDefined();
  cleanup();

  stubApi({
    "/api/claims": [WAITING],
    "/api/runs/latest": { ...RUN, todos: [] },
  });
  render(<QueuePage />);
  expect(await screen.findByText("No to-do list yet.")).toBeDefined();
});

it("shows an error from the backend", async () => {
  stubApi({ "/api/runs/latest": null });
  render(<QueuePage />);
  expect((await screen.findByRole("alert")).textContent).toBe(
    "There is no /api/claims",
  );
});
