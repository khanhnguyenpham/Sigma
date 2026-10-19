import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AlertOpportunity } from "../src/components/AlertOpportunity";
import { type Run } from "../src/api/client";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
const run = (id: string) =>
  ({ id, kind: "alert_replay", status: "complete" }) as Run;
it("shows the replay ceiling separately and discards it immediately on run change", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((url) =>
    String(url).includes("/old/")
      ? Promise.resolve({
          ok: true,
          json: async () => ({
            diagnostic: {
              event_denominator: 2867,
              short_notice_events: 1550,
              eligible_early_events: 1317,
              missed_eligible_events: 331,
              observed_early_rate: 986 / 2867,
              theoretical_max_early_rate: 1317 / 2867,
              histogram: [],
            },
          }),
        } as Response)
      : new Promise(() => {}),
  );
  const view = render(<AlertOpportunity run={run("old")} />);
  expect(await screen.findByText("45,9%")).toBeVisible();
  expect(screen.getByText("34,4%")).toBeVisible();
  expect(screen.getByText(/không phải trần chất lượng/)).toBeVisible();
  view.rerender(<AlertOpportunity run={run("new")} />);
  expect(screen.queryByText("45,9%")).toBeNull();
  expect(screen.getByRole("status")).toBeVisible();
});
it("does not invent replay diagnostics for snapshots or unlabeled rates", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: true,
    json: async () => ({
      diagnostic: {
        event_denominator: 0,
        short_notice_events: 0,
        eligible_early_events: 0,
        missed_eligible_events: 0,
        observed_early_rate: null,
        theoretical_max_early_rate: null,
        histogram: [],
      },
    }),
  } as Response);
  const view = render(
    <AlertOpportunity run={{ ...run("snapshot"), kind: "stock_projection" }} />,
  );
  expect(fetch).not.toHaveBeenCalled();
  view.rerender(<AlertOpportunity run={run("empty")} />);
  await screen.findByText(/Trong 0 sự kiện/);
  expect(screen.getAllByText("—")).toHaveLength(2);
  expect(screen.queryByText("0,0%")).toBeNull();
});
