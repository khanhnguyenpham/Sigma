import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import App from "../src/App";
import type { Row, Run } from "../src/types/api";

vi.mock("../src/components/configuration/ScenarioResults", () => ({
  ScenarioResults: ({ run }: { run: Run }) => <div>Kết quả đã chốt {run.id}</div>,
}));
const reply = (body: unknown, status = 200) => Promise.resolve({ ok: status < 400, status, json: async () => body } as Response);
const page = (items: unknown[]) => ({ items, total: items.length, page: 1, page_size: 100 });
const scene = { id: 1, name: "Base", code: "base", version: 1, settings: { cover_days: 7, safety_multiplier: 1 } };
const forecast: Run = {
  id: "forecast-parent", kind: "forecast", status: "complete", as_of_date: "2025-12-31", observation_end: "2025-12-31",
  source_import_run_id: "source-parent", forecast_run_id: null, scenario_id: null, error_code: null, period_start: null, period_end: null,
  result_summary: { origins: 185, stock_projection_origins: ["2025-10-31"] }, config_version: "synthetic",
  assumption_version: "synthetic", target_version: "synthetic", created_at: "2026-01-01T00:00:00Z",
};
function fixture({ initialRun, rejectRun = false, parentError = false }: { initialRun?: Run; rejectRun?: boolean; parentError?: boolean } = {}) {
  const scenarios: Row[] = [scene], writes: { path: string; body: Row; key?: string }[] = [];
  let run = initialRun;
  vi.spyOn(globalThis, "fetch").mockImplementation((input, options) => {
    const url = new URL(String(input), location.origin), path = url.pathname.replace("/api/v1", "");
    if (options?.method === "POST") {
      const body = options.body ? JSON.parse(String(options.body)) : {};
      writes.push({ path, body, key: (options.headers as Record<string, string>)["Idempotency-Key"] });
      if (path === "/scenarios") {
        const saved = { ...body, id: 3, version: 2 }; scenarios.push(saved); return reply(saved);
      }
      if (rejectRun) return reply({ error: { code: "demo_run_limit", message: "quota", details: { retry_after_seconds: 20 } } }, 429);
      run = { ...forecast, id: "queued-run", kind: String(body.kind ?? initialRun?.kind), status: "queued",
        scenario_id: Number(body.scenario_id ?? initialRun?.scenario_id), as_of_date: String(body.as_of_date ?? "2025-10-31"),
        forecast_run_id: forecast.id, result_summary: {} };
      return reply({ run_id: run.id }, 202);
    }
    if (path === "/scenarios") return reply(page(scenarios));
    if (path === "/runs") {
      if (url.searchParams.has("kind")) {
        if (parentError) return reply({ error: { code: "database_unavailable" } }, 503);
        return reply(page(url.searchParams.get("kind") === "forecast" ? [forecast] : []));
      }
      return reply(page(run ? [run] : [forecast]));
    }
    if (path.startsWith("/runs/")) return run && path === `/runs/${run.id}` ? reply(run) : reply({ error: { code: "not_found" } }, 404);
    if (path === "/products") return reply(page([{ trade_schema_ready: true }]));
    return reply(page([]));
  });
  return { writes, setStatus(status: string) { if (run) run = { ...run, status }; } };
}
beforeEach(() => { history.replaceState(null, "", "/#scenarios"); vi.spyOn(window, "scrollTo").mockImplementation(() => {}); });
afterEach(() => { cleanup(); vi.restoreAllMocks(); history.replaceState(null, "", "/"); });

it("saves without running, selects the returned version and keeps progress/results on the same page", async () => {
  const state = fixture(); render(<App />);
  const name = await screen.findByLabelText("Tên kịch bản");
  expect(location.search).not.toContain("run_id");
  fireEvent.change(name, { target: { value: "My scenario" } });
  fireEvent.change(screen.getByLabelText("Mã kịch bản"), { target: { value: "my_scenario" } });
  fireEvent.click(screen.getByRole("button", { name: "Lưu thiết lập" }));
  await waitFor(() => expect(screen.getByLabelText("Kịch bản / phiên bản")).toHaveValue("3"));
  expect(state.writes.map((write) => write.path)).toEqual(["/scenarios"]);
  expect(location.search).toContain("scenario_id=3");
  await waitFor(() => expect(screen.getByRole("button", { name: "Chạy kịch bản" })).toBeEnabled());
  fireEvent.change(screen.getByLabelText("Tên kịch bản"), { target: { value: "Unsaved" } });
  expect(screen.getByRole("button", { name: "Chạy kịch bản" })).toBeDisabled();
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  fireEvent.click(screen.getByRole("button", { name: "Sản phẩm" }));
  expect(confirm).toHaveBeenCalledOnce(); expect(location.hash).toBe("#scenarios");
  fireEvent.change(screen.getByLabelText("Tên kịch bản"), { target: { value: "My scenario" } });
  fireEvent.click(screen.getByRole("button", { name: "Chạy kịch bản" }));
  await waitFor(() => expect(location.search).toContain("run_id=queued-run"));
  expect(location.hash).toBe("#scenarios"); expect(state.writes[1].body.scenario_id).toBe(3);
  expect(state.writes[1].body).not.toHaveProperty("receiving_warehouse_id");
  await screen.findByText(/Bạn có thể rời trang/);
  expect(screen.queryByText("Kết quả đã chốt queued-run")).toBeNull();
  state.setStatus("complete"); act(() => window.dispatchEvent(new Event("sigma:refresh")));
  await screen.findByText("Kết quả đã chốt queued-run");
  expect(location.hash).toBe("#scenarios"); expect(state.writes).toHaveLength(2);
});

it("restores the exact run through the configuration alias and blocks a mismatched scenario link", async () => {
  fixture({ initialRun: { ...forecast, id: "exact-run", kind: "stock_projection", scenario_id: 1 } });
  history.replaceState(null, "", "/?scenario_id=99&run_id=exact-run#configuration");
  const view = render(<App />);
  await screen.findByText("Kịch bản trong liên kết không khớp lượt chạy.");
  expect(screen.queryByText("Kết quả đã chốt exact-run")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Mở đúng kịch bản của lượt chạy" }));
  await screen.findByText("Kết quả đã chốt exact-run");
  expect(location.hash).toBe("#scenarios"); expect(location.search).toContain("scenario_id=1");
  view.unmount(); render(<App />);
  await screen.findByText("Kết quả đã chốt exact-run");
});

it("retains settings on quota rejection and reuses the idempotency key", async () => {
  const state = fixture({ rejectRun: true }); history.replaceState(null, "", "/?scenario_id=1#scenarios"); render(<App />);
  const run = await screen.findByRole("button", { name: "Chạy kịch bản" });
  await waitFor(() => expect(run).toBeEnabled()); fireEvent.click(run);
  await screen.findByRole("alert"); expect(location.search).not.toContain("run_id");
  expect(screen.getByLabelText("Tên kịch bản")).toHaveValue("Base");
  fireEvent.click(run); await waitFor(() => expect(state.writes).toHaveLength(2));
  expect(state.writes[1].key).toBe(state.writes[0].key);
});

it("blocks running when parent data fails and retries a failed run as a new run", async () => {
  const unavailable = fixture({ parentError: true }); history.replaceState(null, "", "/?scenario_id=1#scenarios");
  const view = render(<App />);
  await screen.findByRole("button", { name: "Chạy kịch bản" });
  await waitFor(() => expect(screen.getByRole("button", { name: "Chạy kịch bản" })).toBeDisabled());
  expect(unavailable.writes).toHaveLength(0); view.unmount(); vi.restoreAllMocks();
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  const failed = fixture({ initialRun: { ...forecast, id: "failed-run", kind: "stock_projection", status: "failed", scenario_id: 1 } });
  history.replaceState(null, "", "/?scenario_id=1&run_id=failed-run#scenarios"); render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Thử lại với cấu hình hiện tại" }));
  await waitFor(() => expect(location.search).toContain("run_id=queued-run"));
  expect(failed.writes[0].path).toBe("/runs/failed-run/retry"); expect(location.hash).toBe("#scenarios");
});
