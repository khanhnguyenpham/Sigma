import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SupplyImpactResult, SupplyImpactTab } from "../src/components/configuration/SupplyImpactResult";
import type { Row, Run } from "../src/types/api";
import type { Context } from "../src/types/context";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });
const internal: Row = { item_id: 631, sku: "D5G-7D", product_type: "eSIM", carrier: "LG U+", city: "Busan", window_origin: "2025-10-31",
  internal_status: "stopped", replenishment_allowed: false, sales_allowed: true, total_qty: 1, sellable_qty: 1, blocked_qty: 0,
  pending_qty: 5, receipts_qty: 5, source_sales_qty: 4, fulfilled_qty: 4, actual_blocked_qty: 0, shortage_qty: 0,
  ss: 2, rop: 9, inventory_position: 6, q_policy: 5, q_final: 0, cap_reason: "internal_stopped" };
const provider: Row = { ...internal, item_id: 349, sku: "D3G-5D", provider_status: "stopped", internal_status: "active",
  sales_allowed: false, sellable_qty: 0, blocked_qty: 1, pending_qty: 0, receipts_qty: 0, source_sales_qty: 3,
  fulfilled_qty: 0, actual_blocked_qty: 3, cap_reason: "provider_blocked" };

it("shows both frozen examples, rights, stock split and capped order directly", () => {
  const onItem = vi.fn();
  render(<SupplyImpactResult impacts={{ internal: { total: 2, item: internal }, provider: { total: 1, item: provider } }} date="2025-11-07" onItem={onItem} />);
  expect(screen.getByText(/Số liệu ngày 2025-11-07/)).toBeVisible();
  const cards = screen.getAllByRole("article");
  expect(within(cards[0]).getByText(/1\/2 mặt hàng/)).toBeVisible();
  expect(within(cards[0]).getByText("Được phép")).toBeVisible();
  expect(within(cards[1]).getAllByText("Bị chặn")).toHaveLength(2);
  expect(screen.getAllByText("5 → 0 đơn vị")).toHaveLength(2);
  expect(within(cards[0]).getAllByText("Đã ngừng nhập nội bộ")).toHaveLength(2);
  fireEvent.click(within(cards[1]).getByText("Xem số liệu trong ngày và ngưỡng nhập"));
  expect(within(cards[1]).getByText("Nhu cầu bị chặn bán").nextElementSibling).toHaveTextContent("3");
  expect(within(cards[1]).getByText("Thiếu hàng được phép bán").nextElementSibling).toHaveTextContent("0");
  fireEvent.click(screen.getByRole("button", { name: "D5G-7D" }));
  expect(onItem).toHaveBeenCalledWith(internal, "inventory");
});

it("does not turn absent diagnostics into zero or scheduled stops into blocked sales", () => {
  render(<SupplyImpactResult impacts={{ internal: { total: 0, item: null }, provider: { total: 1, item: { ...provider,
    provider_status: "scheduled_stop", sales_allowed: true, replenishment_allowed: true, q_policy: null, q_final: 0,
    cap_reason: "eta_at_or_after_provider_stop", quantity_diagnostics_available: false } } }} date="2025-10-31" onItem={vi.fn()} />);
  expect(screen.getByText(/Không có mặt hàng thuộc nhóm/)).toBeVisible();
  expect(screen.getByText("Nhà mạng sắp ngừng sản phẩm")).toBeVisible();
  expect(screen.getByText("— → 0 đơn vị")).toBeVisible();
  expect(screen.getAllByText("Được phép")).toHaveLength(2);
  expect(screen.getByText("Hàng về từ ngày nhà mạng ngừng sản phẩm")).toBeVisible();
});

it("keeps historical runs without the feature unchanged", () => {
  const { container } = render(<SupplyImpactResult impacts={undefined} date="2025-11-07" onItem={vi.fn()} />);
  expect(container).toBeEmptyDOMElement();
});

it("loads the dedicated tab and clears the previous day while loading", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: async () => ({
    context: {}, summary: { inventory_available: true }, attention: [], incoming: [], route_stock: [],
    supply_impacts: { internal: { total: 1, item: internal }, provider: { total: 1, item: provider } },
  }) } as Response).mockImplementationOnce(() => new Promise(() => {}));
  const run = { id: "frozen", kind: "policy_replay", status: "complete", result_summary: {} } as Run;
  const ctx = { origin: "2025-11-07", itemId: "", warehouseId: "", supplierId: "", productType: "" } as Context;
  const props = { run, ctx, onItem: vi.fn() };
  const view = render(<SupplyImpactTab {...props} />);
  expect(await screen.findByRole("button", { name: "D5G-7D" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Ảnh hưởng ngừng cung cấp" })).toBeVisible();
  view.rerender(<SupplyImpactTab {...props} ctx={{ ...ctx, origin: "2025-11-08", itemId: "349" }} />);
  expect(screen.queryByRole("button", { name: "D5G-7D" })).toBeNull();
  expect(fetcher.mock.calls[1][0]).toContain("as_of_date=2025-11-08");
  expect(fetcher.mock.calls[1][0]).toContain("item_id=349");
});
