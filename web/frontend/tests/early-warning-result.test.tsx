import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { EarlyWarningResult } from "../src/components/alerts/EarlyWarningResult";
import type { Run } from "../src/types/api";
import type { AppContextState } from "../src/hooks/useAppContext";
import { ScenarioResults } from "../src/components/configuration/ScenarioResults";
vi.mock("../src/pages/Overview", () => ({ Overview: () => <div /> }));
const run: Run = { id: "replay", kind: "alert_replay", status: "complete", as_of_date: "2025-09-30", observation_end: "2025-12-31",
  source_import_run_id: "source", forecast_run_id: "forecast", scenario_id: 1, config_version: "synthetic", assumption_version: "synthetic",
  target_version: "synthetic", error_code: null, created_at: "2026-11-04T00:00:00Z", period_start: "2025-10-01", period_end: "2025-10-14",
  result_summary: { alert_metrics: { early_rate: 150 / 461, early_numerator: 150, event_denominator: 461,
    precision: 302 / 441, recall: 302 / 461, excluded_count: 199 } } };
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it("shows the stored whole-run early-warning rate, counts and separate precision/recall", () => {
  render(<EarlyWarningResult run={run} />);
  expect(screen.getByText("32,5%")).toBeVisible();
  expect(screen.getByText("150/461 sự kiện cạn đủ điều kiện")).toBeVisible();
  expect(screen.getByText("68,5%")).toBeVisible();
  expect(screen.getByText("65,5%")).toBeVisible();
  expect(screen.getByText(/không phải phần trăm chính xác/)).toBeVisible();
  expect(screen.getByText(/bộ lọc kho, ngày và bảng không thay mẫu số/)).toBeVisible();
});

it("keeps measured zero distinct from an undefined rate with no events", () => {
  const view = render(<EarlyWarningResult run={{ ...run, result_summary: { alert_metrics: { early_rate: 0, early_numerator: 0, event_denominator: 3 } } }} />);
  expect(screen.getByText("0,0%")).toBeVisible();
  view.rerender(<EarlyWarningResult run={{ ...run, result_summary: { alert_metrics: { early_rate: null, early_numerator: 0, event_denominator: 0 } } }} />);
  expect(screen.getByText("Chưa xác định")).toBeVisible();
  expect(screen.queryByText("0,0%")).toBeNull();
  expect(screen.getByText(/Không có sự kiện cạn đủ điều kiện/)).toBeVisible();
});

it("distinguishes an unmeasured snapshot from an explicitly labelled related replay result", () => {
  const open = vi.fn();
  const view = render(<EarlyWarningResult run={run} />);
  const snapshot = { ...run, id: "snapshot", kind: "stock_projection", as_of_date: "2025-10-31" };
  view.rerender(<EarlyWarningResult run={snapshot} />);
  expect(screen.queryByText("32,5%")).toBeNull();
  expect(screen.getByText(/Lượt này chưa có tỷ lệ/)).toBeVisible();
  view.rerender(<EarlyWarningResult run={snapshot} replay={run} onOpenReplay={open} />);
  expect(screen.getByText("32,5%")).toBeVisible();
  expect(screen.getByText(/chưa phải tỷ lệ đo riêng cho lượt snapshot tại ngày 2025-10-31/)).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Mở lượt Kiểm tra cảnh báo này" }));
  expect(open).toHaveBeenCalledOnce();
});

it("does not display an inconsistent stored ratio as a valid result", () => {
  render(<EarlyWarningResult run={{ ...run, result_summary: { alert_metrics: { early_rate: .9, early_numerator: 1, event_denominator: 10 } } }} />);
  expect(screen.queryByText("90,0%")).toBeNull();
  expect(screen.getByText("Chưa xác định")).toBeVisible();
});

it("links only matching replays and keeps comparison in its dedicated scenario tab", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue({ ok: true, json: async () => ({ items: [], total: 0 }) } as Response);
  const snapshot = { ...run, id: "snapshot", kind: "stock_projection", as_of_date: "2025-10-31", scenario_id: 1,
    forecast_run_id: "forecast", source_import_run_id: "source" };
  const matching = { ...run, scenario_id: 1, forecast_run_id: "forecast", source_import_run_id: "source" };
  const others = [{ ...matching, id: "other-scenario", scenario_id: 2 },
    { ...matching, id: "other-forecast", forecast_run_id: "other" },
    { ...matching, id: "other-source", source_import_run_id: "other" },
    { ...matching, id: "unfinished", status: "running" }];
  const openScenarios = vi.fn();
  const app = { run: snapshot, runs: [snapshot, ...others, matching], page: "scenarios", openScenarios,
    ctx: { runId: snapshot.id, origin: "2025-10-31", warehouseId: "", itemId: "", supplierId: "", productType: "" },
    catalog: { data: { items: [] } }, items: { data: { items: [] } }, suppliers: { data: { items: [] } },
    setCtx: vi.fn(), selectRun: vi.fn(), navigate: vi.fn(), openItem: vi.fn() } as unknown as AppContextState;
  const view = render(<ScenarioResults app={app} run={snapshot} />);
  const nav = screen.getByRole("navigation", { name: "Kết quả của lượt chạy" });
  const result = screen.getByRole("heading", { name: "Kết quả cảnh báo sớm trước ít nhất 7 ngày" });
  expect(nav.compareDocumentPosition(result) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.getByText("32,5%")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Mở lượt Kiểm tra cảnh báo này" }));
  expect(openScenarios).toHaveBeenCalledWith(matching.id);
  view.rerender(<ScenarioResults app={{ ...app, runs: [snapshot, ...others] }} run={snapshot} />);
  expect(screen.queryByRole("button", { name: "Mở lượt Kiểm tra cảnh báo này" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Dự kiến bán" })).toBeNull();
  expect(screen.queryByText("32,5%")).toBeNull();
  expect(fetcher.mock.calls.some(([path]) => String(path).includes("/forecasts/origins"))).toBe(false);
  fireEvent.click(screen.getByRole("button", { name: "So sánh dự báo / thực tế" }));
  expect(await screen.findByRole("heading", { name: "So sánh dự báo và thực tế 14 ngày" })).toBeVisible();
  expect(screen.queryByRole("heading", { name: "Kết quả cảnh báo sớm trước ít nhất 7 ngày" })).toBeNull();
});
