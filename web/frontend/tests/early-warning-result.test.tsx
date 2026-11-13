import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { EarlyWarningResult } from "../src/components/alerts/EarlyWarningResult";
import type { Run } from "../src/types/api";
import type { AppContextState } from "../src/hooks/useAppContext";
import { ScenarioResults } from "../src/components/configuration/ScenarioResults";
const run: Run = { id: "replay", kind: "alert_replay", status: "complete", as_of_date: "2025-09-30", observation_end: "2025-12-31",
  source_import_run_id: "source", forecast_run_id: "forecast", scenario_id: 1, config_version: "synthetic", assumption_version: "synthetic",
  target_version: "synthetic", error_code: null, created_at: "2026-11-04T00:00:00Z", period_start: "2025-10-01", period_end: "2025-10-14",
  result_summary: { alert_metrics: { early_rate: 150 / 461, early_numerator: 150, event_denominator: 461,
    precision: 302 / 441, recall: 302 / 461, excluded_count: 199 } } };
const diagnostic = { observed_early_numerator: 150, eligible_early_events: 300,
  eligible_detection_rate: .5, event_denominator: 461, observed_early_rate: 150 / 461,
  short_notice_events: 161 };
const response = (data: unknown) => ({ ok: true, json: async () => data }) as Response;
beforeEach(() => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (path) => {
    if (String(path).includes("/alert-opportunities")) return response({ diagnostic });
    if (String(path).includes("/workspace")) return response({
      context: {}, summary: { inventory_available: true, on_hand_units: 42, item_count: 7 },
      attention: [], incoming: [], route_stock: [], warehouse_stock: [],
    });
    return response({ items: [], total: 0 });
  });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it("loads the purchasing plan's own evaluation", async () => {
  vi.mocked(fetch).mockResolvedValueOnce(response({ diagnostic: {
    ...diagnostic, detected_events: 302, recall: 302 / 461,
    warnings_with_receipt: 12, warnings_with_incomplete_followup: 9,
    blocked_sales_item_days: 8, warnings_with_sales_block: 3,
  } }));
  render(<EarlyWarningResult run={{ ...run, kind: "policy_replay", id: "purchasing" }} />);
  expect(await screen.findByText("50,0%")).toBeVisible();
  expect(screen.getByText(/12 cảnh báo có lô mới về/)).toBeVisible();
  expect(screen.getByText(/chặn bán trong 8 mặt hàng-ngày.*3 cảnh báo chưa gặp đợt cạn/)).toBeVisible();
  expect(vi.mocked(fetch).mock.calls.map(([path]) => String(path))).toEqual([
    "/api/v1/runs/purchasing/policy-alert-evaluation",
  ]);
});

it("defaults to cases with time to warn, keeping the full-run rate and precision/recall visible", async () => {
  render(<EarlyWarningResult run={run} />);
  expect(await screen.findByText("50,0%")).toBeVisible();
  expect(screen.getByText("150/300 ca có đủ thời gian báo sớm")).toBeVisible();
  expect(screen.getByText(/161 ca.*32,5% \(150\/461\)/)).toBeVisible();
  expect(screen.getByText("68,5%")).toBeVisible();
  expect(screen.getByText("65,5%")).toBeVisible();
  expect(screen.getByText("Kỳ hồi cứu UTC · 2025-10-01 đến 2025-10-14")).toBeVisible();
});

it("keeps measured zero distinct from an undefined rate with no eligible events", async () => {
  vi.mocked(fetch)
    .mockResolvedValueOnce(response({ diagnostic: { observed_early_numerator: 0, eligible_early_events: 3, eligible_detection_rate: 0 } }))
    .mockResolvedValueOnce(response({ diagnostic: { observed_early_numerator: 0, eligible_early_events: 0, eligible_detection_rate: null, event_denominator: 3, short_notice_events: 3 } }));
  const view = render(<EarlyWarningResult run={run} />);
  expect(await screen.findByText("0,0%")).toBeVisible();
  view.rerender(<EarlyWarningResult run={{ ...run, id: "no-eligible-cases" }} />);
  expect(await screen.findByText(/Không có sự kiện cạn đủ thời gian/)).toBeVisible();
  expect(screen.getByText("Chưa xác định")).toBeVisible();
  expect(screen.queryByText("0,0%")).toBeNull();
});

it("shows an empty result when the selected replay has no saved evaluation", () => {
  render(<EarlyWarningResult run={{ ...run, result_summary: {} }} />);
  expect(screen.getByText("Lượt này chưa có kết quả chấm cảnh báo cạn hàng.")).toBeVisible();
  expect(fetch).not.toHaveBeenCalled();
});

it("does not display an inconsistent eligibility ratio as a valid result", async () => {
  vi.mocked(fetch).mockResolvedValueOnce(response({ diagnostic: { ...diagnostic, eligible_detection_rate: .9 } }));
  render(<EarlyWarningResult run={run} />);
  expect(await screen.findByText(/150\/300 ca có đủ thời gian/)).toBeVisible();
  expect(screen.queryByText("90,0%")).toBeNull();
  expect(screen.getByText("Chưa xác định")).toBeVisible();
});

it("separates the stock and alert summaries when switching runs and keeps the detail tabs", async () => {
  const fetcher = vi.mocked(fetch);
  const snapshot = { ...run, id: "snapshot", kind: "stock_projection", period_start: null, period_end: null, result_summary: {} };
  const app = { run: snapshot, runs: [snapshot, run], page: "scenarios", openScenarios: vi.fn(),
    ctx: { runId: snapshot.id, origin: snapshot.as_of_date, warehouseId: "", itemId: "", supplierId: "", productType: "" },
    catalog: { data: { items: [] } }, items: { data: { items: [] } }, suppliers: { data: { items: [] } },
    setCtx: vi.fn(), selectRun: vi.fn(), navigate: vi.fn(), openItem: vi.fn() } as unknown as AppContextState;
  const view = render(<ScenarioResults app={app} run={snapshot} />);
  expect(await screen.findByText("42")).toBeVisible();
  expect(screen.getByText("Tồn hiện có")).toBeVisible();
  expect(screen.queryByRole("heading", { name: "Kết quả kiểm tra cảnh báo" })).toBeNull();
  expect(fetcher.mock.calls.map(([path]) => String(path))).toEqual([expect.stringContaining("/runs/snapshot/workspace?")]);

  fetcher.mockClear();
  view.rerender(<ScenarioResults app={{ ...app, run, ctx: { ...app.ctx, runId: run.id } }} run={run} />);
  const nav = screen.getByRole("navigation", { name: "Kết quả của lượt chạy" });
  const result = screen.getByRole("heading", { name: "Kết quả kiểm tra cảnh báo" });
  expect(nav.compareDocumentPosition(result) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(await screen.findByText("50,0%")).toBeVisible();
  expect(screen.queryByText("Tồn hiện có")).toBeNull();
  expect(screen.queryByRole("region", { name: "Bộ lọc cùng lượt chạy" })).toBeNull();
  expect(fetcher.mock.calls.map(([path]) => String(path))).toEqual(["/api/v1/runs/replay/alert-opportunities"]);
  fireEvent.click(screen.getByRole("button", { name: /^Ngừng cung cấp$/ }));
  expect(await screen.findByText(/Lượt chạy này chưa có dữ liệu ảnh hưởng ngừng cung cấp/)).toBeVisible();
  expect(screen.getByRole("region", { name: "Bộ lọc cùng lượt chạy" })).toBeVisible();
  expect(fetcher.mock.calls.some(([path]) => String(path).includes("/runs/replay/workspace?"))).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "So sánh dự báo / thực tế" }));
  expect(await screen.findByRole("heading", { name: "So sánh dự báo và thực tế 14 ngày" })).toBeVisible();
  expect(screen.queryByRole("heading", { name: "Kết quả kiểm tra cảnh báo" })).toBeNull();
});
