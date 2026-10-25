import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { MonthlyForecast } from "../src/components/forecast/MonthlyForecast";
import { type Run } from "../src/types/api";
import { type Context } from "../src/types/context";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
const run = (id: string) =>
  ({ id, kind: "forecast", status: "complete" }) as Run;
const ctx = {
  runId: "old",
  origin: "2025-12-31",
  warehouseId: "",
  itemId: "341",
  supplierId: "",
  productType: "",
} as Context;
it("shows total-30 acceptance and discards benchmark immediately when run changes", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
    if (String(url).includes("/new/")) return new Promise(() => {});
    return Promise.resolve({
      ok: true,
      json: async () =>
        String(url).includes("monthly-summary")
          ? {
              context: {
                benchmark_run_id: "synthetic",
                benchmark_package_id: "abc",
                acceptance_version: "r05-sales-30d-v1",
              },
              summary: {
                routes_below_20_pct: 10,
                expected_top_routes: 10,
                meets_r05: true,
                mean_mape_positive_pct: 11.62,
                minimum_coverage: 1,
                pairs_per_route: 63,
                baselines: [],
              },
            }
          : { items: [], total: 0 },
    } as Response);
  });
  const view = render(<MonthlyForecast run={run("old")} ctx={ctx} />);
  expect(await screen.findByText("10/10")).not.toBeVisible();
  fireEvent.click(screen.getByText("Chất lượng & nguồn dự báo"));
  expect(screen.getByText("10/10")).toBeVisible();
  expect(screen.getByText("11,62%")).toBeVisible();
  expect(screen.getByText(/không phải holdout độc lập/)).toBeVisible();
  expect(
    fetch.mock.calls.every(([url]) => !String(url).includes("item_id=")),
  ).toBe(true);
  fireEvent.change(screen.getByLabelText("Nhịp chấm tổng 30"), {
    target: { value: "nonoverlapping_30d" },
  });
  expect(
    fetch.mock.calls.some(([url]) =>
      String(url).includes("cadence=nonoverlapping_30d"),
    ),
  ).toBe(true);
  view.rerender(
    <MonthlyForecast run={run("new")} ctx={{ ...ctx, runId: "new" }} />,
  );
  expect(screen.queryByText("10/10")).toBeNull();
  expect(screen.queryByText("11,62%")).toBeNull();
});

it("renders unknown future actual as blank marker and exports the same origin", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: true,
    json: async () => ({
      items: [
        {
          destination_country: "Demo",
          carrier: "Carrier",
          window_start: "2026-01-01",
          target_date: "2026-01-30",
          forecast_qty: 100,
          actual_qty: null,
          metric_eligible: false,
        },
      ],
      total: 1,
    }),
  } as Response);
  render(<MonthlyForecast run={run("future")} ctx={ctx} />);
  expect((await screen.findAllByText("2026-01-30")).length).toBeGreaterThan(0);
  expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  const links = screen.getAllByRole("link");
  expect(
    links.some((link) =>
      link
        .getAttribute("href")
        ?.includes("monthly_forecasts?top10_only=false&as_of_date=2025-12-31"),
    ),
  ).toBe(true);
});
