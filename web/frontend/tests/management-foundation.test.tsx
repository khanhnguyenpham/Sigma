import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Table } from "../src/components/ui/Table";
import { State } from "../src/components/ui/State";
import { Pager } from "../src/components/ui/Pager";
import { RunSnapshot } from "../src/components/configuration/RunSnapshot";
import { contextUrl, readContext } from "../src/utils/url";
import type { Run } from "../src/types/api";

afterEach(() => { cleanup(); vi.restoreAllMocks(); history.replaceState(null, "", "/"); });

it("distinguishes missing cells from zero and false, and renders empty tables explicitly", () => {
  const view = render(<Table rows={[{ id: 1, missing: null, quantity: 0, active: false }]}
    columns={[{ key: "missing", label: "Thông tin" }, { key: "quantity", label: "Số lượng" }, { key: "active", label: "Hoạt động" }]} />);
  expect(screen.getByRole("cell", { name: "Không có" })).toBeVisible();
  expect(screen.getByRole("cell", { name: "0" })).toBeVisible();
  expect(screen.getByRole("cell", { name: "false" })).toBeVisible();
  view.rerender(<Table rows={[]} columns={[{ key: "sku", label: "Sản phẩm" }, { key: "quantity", label: "Số lượng" }]} />);
  expect(screen.getByRole("cell", { name: "Không có dữ liệu" })).toHaveAttribute("colspan", "2");
});

it("does not show stale rows or an empty result while a table loads", () => {
  render(<Table loading rows={[{ sku: "OLD" }]} columns={[{ key: "sku", label: "Sản phẩm" }]} />);
  expect(screen.getByRole("region")).toHaveAttribute("aria-busy", "true");
  expect(screen.getByRole("status")).toHaveTextContent("Đang tải dữ liệu");
  expect(screen.queryByText("OLD")).toBeNull();
  expect(screen.queryByText("Không có dữ liệu")).toBeNull();
});

it("shows loading before empty and keeps retry available on errors", () => {
  const refresh = vi.fn(); window.addEventListener("sigma:refresh", refresh);
  const view = render(<State loading empty />);
  expect(screen.getByRole("status")).toHaveAttribute("aria-busy", "true");
  expect(screen.queryByText(/Không có bản ghi/)).toBeNull();
  view.rerender(<State error={new Error("offline")} empty />);
  fireEvent.click(screen.getByRole("button", { name: "Thử tải lại" }));
  expect(refresh).toHaveBeenCalledTimes(1);
  window.removeEventListener("sigma:refresh", refresh);
});

it("uses the actual page size for snapshot paging without changing the default table page size", () => {
  const next = vi.fn();
  render(<Pager page={1} total={26} pageSize={25} onChange={next} />);
  fireEvent.click(screen.getByRole("button", { name: "Sau →" }));
  expect(next).toHaveBeenCalledWith(2);
});

it("preserves valid inventory state in a deep link and ignores unknown states", () => {
  history.replaceState(null, "", "/?run_id=plan&inventory_state=pending_covers#inventory");
  expect(readContext().inventoryState).toBe("pending_covers");
  expect(new URLSearchParams(contextUrl(readContext())).get("inventory_state")).toBe("pending_covers");
  history.replaceState(null, "", "/?inventory_state=invalid#inventory");
  expect(readContext().inventoryState).toBeUndefined();
});

const snapshot = { scenario: { name: "Frozen", version: 1 }, versions: { config: "v1" },
  parameters: { cover_days: 7, initial_stock_history_days: 28, safety_multiplier: 0, lead_time_days: 7, review_days: 1, horizon_days: 14 },
  policies: { items: [{ sku: "SIM-A", fixed_order_qty: 15 }], total: 26, page: 1, page_size: 25 },
  receipts_initial: [], policy_overrides: [], supply_schedule: { internal_stops: [], provider_stops: [] } };

it("loads a frozen snapshot only when opened, paginates and discards it on run changes", async () => {
  const requests: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    requests.push(String(input));
    return { ok: true, json: async () => snapshot } as Response;
  });
  const run = { id: "a", as_of_date: "2025-10-31" } as Run;
  const view = render(<RunSnapshot key={run.id} run={run} />);
  expect(requests).toHaveLength(0);
  fireEvent.click(screen.getByText("Thiết lập đã chốt của lượt chạy"));
  const facts = (await screen.findByText("Hệ số tồn an toàn")).parentElement!;
  expect(within(facts).getByText("0")).toBeVisible();
  expect(screen.queryByText("SIM-A")).toBeNull();
  fireEvent.click(screen.getByRole("tab", { name: "Chính sách" }));
  expect(await screen.findByText("SIM-A")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Sau →" }));
  await waitFor(() => expect(requests.some((path) => path.includes("page=2"))).toBe(true));
  view.rerender(<RunSnapshot key="b" run={{ ...run, id: "b" }} />);
  expect(screen.queryByText("SIM-A")).toBeNull();
});

it("distinguishes the 28-day stock basis from a historical 90-day zero-sales fallback", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue({ ok: true, json: async () => ({ ...snapshot,
    parameters: { ...snapshot.parameters, zero_sales_fallback_days: 90 } }) } as Response);
  render(<RunSnapshot run={{ id: "legacy", as_of_date: "2025-10-31" } as Run} />);
  fireEvent.click(screen.getByText("Thiết lập đã chốt của lượt chạy"));
  const fallback = await screen.findByText("Dự phòng nếu 28 ngày không bán");
  expect(fallback.parentElement).toHaveTextContent("90 ngày khi đủ quan sát");
  expect(screen.getByText("Lịch sử tính tồn đầu").parentElement).toHaveTextContent("28 ngày");
});
