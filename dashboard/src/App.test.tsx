import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { CLAIM, WAITING, stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.location.hash = "";
});

it("shows the queue by default", async () => {
  stubApi({ "/api/claims": [WAITING] });
  render(<App />);
  expect(
    await screen.findByRole("heading", { name: "Claims queue" }),
  ).toBeDefined();
  expect(
    screen.getByRole("link", { name: "Queue" }).getAttribute("aria-current"),
  ).toBe("page");
});

it("shows the agent's instructions, read only", async () => {
  stubApi({
    "/api/instructions": { instructions: "You are the UnderCover Agent." },
  });
  window.location.hash = "#/instructions";
  render(<App />);
  expect(
    await screen.findByText("You are the UnderCover Agent."),
  ).toBeDefined();
  expect(screen.queryByRole("textbox")).toBeNull();
});

it("follows the address to a claim", async () => {
  stubApi({
    "/api/claims": [WAITING],
    "/api/claims/CLM-1001": CLAIM,
    "/api/claims/CLM-1001/steps": [],
  });
  render(<App />);
  await screen.findByRole("heading", { name: "Claims queue" });

  act(() => {
    window.location.hash = "#/claims/CLM-1001";
    window.dispatchEvent(new HashChangeEvent("hashchange"));
  });
  expect(
    await screen.findByRole("heading", { name: "CLM-1001 Waiting" }),
  ).toBeDefined();
});

it("shows an error when the instructions fail to load", async () => {
  stubApi({});
  window.location.hash = "#/instructions";
  render(<App />);
  expect((await screen.findByRole("alert")).textContent).toBe(
    "There is no /api/instructions",
  );
});
