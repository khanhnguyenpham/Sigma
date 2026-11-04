import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ForecastComparison } from "../src/components/forecast/ForecastComparison";
import { compareForecast14, forecastDay } from "../src/utils/forecastComparison";
import type { Run, Row } from "../src/types/api";
const day = "2025-10-31";
const run = { id: "plan", kind: "stock_projection", status: "complete", as_of_date: day, forecast_run_id: "forecast-parent" } as Run;
const ctx = { runId: run.id, origin: day, warehouseId: "", itemId: "", supplierId: "", productType: "" };
const parts = (id = 1, actual: number | null = 3): Row[] => [1, 2].map(block => ({ warehouse_id: id, destination_country: "Demo",
  carrier: "Carrier " + id, block, forecast_qty: 5, actual_qty: actual, actual_available: actual !== null }));
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it("sums both weeks, counts real zero and leaves incomplete actuals unknown", () => {
  expect(compareForecast14(parts(1, 0), day, false)).toMatchObject({ forecast: 10, actual: 0, difference: 10 });
  const result = compareForecast14([...parts(1, 0), ...parts(2, null)], day, false);
  expect(result).toMatchObject({ forecast: 20, actual: null, difference: null, actualRoutes: 1 });
  expect(result.items[0].actual_qty).toBe(0);
  expect(result.items[1].actual_qty).toBeNull();
  expect(compareForecast14(parts().slice(0, 1), day, false).forecast).toBeNull();
  expect(compareForecast14([parts()[0], parts()[0]], day, false).actual).toBeNull();
});

it("compares exactly D+1 through D+14 for daily allocation, including a month boundary", () => {
  const rows = Array.from({ length: 14 }, (_, index) => ({ warehouse_id: 1, target_date: forecastDay(day, index + 1),
    forecast_qty: 2, actual_qty: 1, actual_available: true }));
  expect(forecastDay(day, 14)).toBe("2025-11-14");
  expect(compareForecast14(rows, day, true)).toMatchObject({ forecast: 28, actual: 14, difference: 14 });
  expect(compareForecast14(rows.slice(0, 13), day, true).forecast).toBeNull();
  expect(compareForecast14([...rows.slice(0, 13), { ...rows[13], target_date: day }], day, true).actual).toBeNull();
});

function fixture({ missing = false, many = false, item = false } = {}) {
  const calls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, options) => {
    const url = new URL(String(input), "http://localhost"); calls.push(url.pathname + url.search);
    expect(options?.method ?? "GET").toBe("GET");
    if (url.pathname.endsWith("/origins")) return { ok: true, json: async () => ({ items: [day, "2025-11-01"].map(as_of_date => ({ as_of_date, actual_available: true })), total: 2 }) } as Response;
    const later = url.searchParams.get("as_of_date") === "2025-11-01";
    const rows = item ? Array.from({ length: 14 }, (_, index) => ({ warehouse_id: 1, target_date: forecastDay(day, index + 1), forecast_qty: 2, actual_qty: 1, actual_available: true }))
      : Array.from({ length: many ? 51 : 1 }, (_, index) => parts(index + 1, missing ? null : later ? 4 : 3)).flat();
    const page = Number(url.searchParams.get("page") ?? 1);
    return { ok: true, json: async () => ({ items: rows.slice((page - 1) * 100, page * 100), total: rows.length }) } as Response;
  });
  return calls;
}

it("changes only the comparison origin and shows both 14-day totals", async () => {
  const calls = fixture(); render(<ForecastComparison run={run} ctx={ctx} />);
  await screen.findByText("2025-11-14", { selector: "strong" });
  await waitFor(() => expect(screen.getByText("Bán thực tế 14 ngày", { selector: "span" }).closest("article")).toHaveTextContent("6"));
  fireEvent.change(screen.getByLabelText("Ngày đánh giá dự báo UTC"), { target: { value: "2025-11-01" } });
  await screen.findByText("2025-11-15", { selector: "strong" });
  await waitFor(() => expect(screen.getByText("Bán thực tế 14 ngày", { selector: "span" }).closest("article")).toHaveTextContent("8"));
  expect(ctx.origin).toBe(day);
  expect(calls.some(path => path.includes("as_of_date=2025-11-01"))).toBe(true);
  expect(screen.getByRole("link", { name: "Xuất CSV" })).toHaveAttribute("href", expect.stringContaining("/runs/forecast-parent/exports/route_forecasts?"));
});

it("loads every result page before showing totals and does not zero-fill missing actuals", async () => {
  const calls = fixture({ missing: true, many: true }); render(<ForecastComparison run={run} ctx={ctx} />);
  await screen.findByText("Chưa đủ thực tế", { selector: "strong" });
  expect(screen.getByText("Dự báo 14 ngày", { selector: "span" }).closest("article")).toHaveTextContent("510");
  expect(calls.some(path => path.includes("page=2"))).toBe(true);
  expect(screen.getByText(/Phần thiếu được để trống/)).toBeVisible();
});

it("uses daily source data for a SKU and excludes receiving and trade filters", async () => {
  const calls = fixture({ item: true });
  render(<ForecastComparison run={run} ctx={{ ...ctx, warehouseId: "201", warehouseScope: "receiving", itemId: "7", salesAllowed: "false", providerStatus: "stopped" }} />);
  await waitFor(() => expect(screen.getByText("Dự báo 14 ngày", { selector: "span" }).closest("article")).toHaveTextContent("28"));
  const path = calls.find(path => path.includes("/forecasts/items?"))!;
  const query = new URL(path, "http://localhost").searchParams;
  expect(Object.fromEntries(query)).toMatchObject({ item_id: "7", aggregate: "route_day", as_of_date: day });
  expect(query.has("warehouse_id") || query.has("receiving_warehouse_id") || query.has("sales_allowed") || query.has("provider_status")).toBe(false);
});
