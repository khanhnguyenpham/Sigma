import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { InventoryFilters } from "../src/components/inventory/InventoryFilters";
import { InventoryActions } from "../src/components/inventory/InventoryActions";
import { RunSnapshot } from "../src/components/configuration/RunSnapshot";
import type { Run } from "../src/types/api";

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });
beforeEach(() => vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true,
  addEventListener: vi.fn(), removeEventListener: vi.fn() }))));
const ctx = { runId: "plan", warehouseId: "1", origin: "2025-10-31", supplierId: "", productType: "", itemId: "" };
const items = [{ id: 1, sku: "ESIM", product_type: "eSIM" }, { id: 2, sku: "SIM", product_type: "physical_SIM" }];

it("keeps mobile filter edits as a draft until Apply and discards them on close", () => {
  const onChange = vi.fn(), onStatus = vi.fn();
  render(<InventoryFilters ctx={ctx} status="pending_covers" onStatus={onStatus} onChange={onChange}
    itemOptions={items} supplierOptions={[{ id: 9, carrier: "Test" }]} />);
  expect(screen.getByLabelText("Trạng thái tồn kho")).toHaveValue("pending_covers");
  expect(screen.queryByLabelText("SKU trong kho")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Lọc khác" }));
  fireEvent.change(screen.getByLabelText("Loại sản phẩm trong kho"), { target: { value: "physical_SIM" } });
  expect(onChange).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Đóng" }));
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(onChange).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Lọc khác" }));
  expect(screen.getByLabelText("Loại sản phẩm trong kho")).toHaveValue("");
  fireEvent.change(screen.getByLabelText("Nhà mạng trong kho"), { target: { value: "9" } });
  fireEvent.change(screen.getByLabelText("Loại sản phẩm trong kho"), { target: { value: "physical_SIM" } });
  fireEvent.change(screen.getByLabelText("SKU trong kho"), { target: { value: "2" } });
  fireEvent.click(screen.getByRole("button", { name: "Áp dụng" }));
  expect(onChange).toHaveBeenCalledExactlyOnceWith({ supplierId: "9", productType: "physical_SIM", itemId: "2" });
  expect(onStatus).not.toHaveBeenCalled();
  expect(screen.queryByRole("dialog")).toBeNull();
});

it("keeps warehouse actions and the scoped CSV available in the compact menu", () => {
  const forecast = vi.fn(), edit = vi.fn(), incoming = vi.fn();
  render(<InventoryActions onEdit={edit} onForecast={forecast} onReplenishment={incoming} exportUrl="/runs/plan/exports/inventory_daily?warehouse_id=1&state=low_stock" />);
  expect(screen.getByRole("button", { name: "Nhập hàng" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Dự báo nhu cầu" })).not.toBeVisible();
  fireEvent.click(screen.getByText("Thao tác kho"));
  expect(screen.getByRole("link", { name: /Xuất CSV/ })).toHaveAttribute("href", "/api/v1/runs/plan/exports/inventory_daily?warehouse_id=1&state=low_stock");
  fireEvent.click(screen.getByRole("button", { name: "Dự báo nhu cầu" }));
  expect(forecast).toHaveBeenCalledOnce();
  expect(screen.getByRole("button", { name: "Dự báo nhu cầu" })).not.toBeVisible();
});

it("opens only one snapshot section, supports keyboard tabs and restores focus on Escape", async () => {
  const fetcher = vi.spyOn(globalThis, "fetch").mockResolvedValue({ ok: true, json: async () => ({
    scenario: {}, versions: {}, parameters: {}, policies: { items: [{ sku: "SIM" }], total: 1 },
    policy_overrides: [], receipts_initial: [], supply_schedule: { internal_stops: [], provider_stops: [] },
  }) } as Response);
  render(<RunSnapshot run={{ id: "snapshot", as_of_date: "2025-10-31" } as Run} />);
  const trigger = screen.getByRole("button", { name: "Thiết lập đã chốt của lượt chạy" });
  trigger.focus(); fireEvent.click(trigger);
  await screen.findByText("Lịch sử tính tồn đầu");
  expect(screen.queryByRole("cell", { name: "SIM" })).toBeNull();
  const summary = screen.getByRole("tab", { name: "Tổng quan" });
  summary.focus(); fireEvent.keyDown(summary, { key: "ArrowRight" });
  expect(screen.getByRole("tab", { name: "Chính sách" })).toHaveFocus();
  expect(await screen.findByRole("cell", { name: "SIM" })).toBeVisible();
  fireEvent.keyDown(screen.getByRole("tab", { name: "Chính sách" }), { key: "End" });
  expect(screen.getByRole("tab", { name: "Lịch cung cấp" })).toHaveFocus();
  expect(screen.getAllByRole("cell", { name: "Không có dữ liệu" })).toHaveLength(2);
  expect(fetcher).toHaveBeenCalledOnce();
  fireEvent(screen.getByRole("dialog"), new Event("cancel", { cancelable: true }));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(trigger).toHaveFocus();
});
