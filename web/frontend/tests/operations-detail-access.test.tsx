import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import App from "../src/App";

const reply = (value: unknown, status = 200) => ({ ok: status < 400, status, json: async () => value }) as Response;
const page = (items: unknown[]) => ({ items, total: items.length, page: 1, page_size: 25 });
const summary = { business_date: "2026-11-19", on_hand_units: 42, pending_orders: 2, late_orders: 0, draft_orders: 0, stocked_items: 3, documents_today: 4 };
const order = { id: 7, number: "PO-07", carrier: "Nhà mạng A", eta: "2026-11-25", status: "ordered", ordered_qty: 10, received_qty: 0 };
const product = { id: 5, sku: "SIM-A", name: "SIM A", product_type: "eSIM", carrier: "Nhà mạng A", supplier_id: 2, destination_country: "Japan", active: true, version: 1, lead_time_days: 5 };
const supplier = { id: 2, carrier: "Nhà mạng A", lead_time_days: 5, version: 1, product_count: 3, active_product_count: 2, countries: ["Japan"], on_hand_qty: 40 };
const policy = { item_id: 5, version: 2, effective_from: "2026-01-01", configured_rop_floor: 4, fixed_order_qty: 20, safety_days: "2.000", warning_horizon_days: 7 };
const audit = { id: 1, created_at: "2026-11-19T04:00:00Z", actor: "Quản trị", action: "created", entity_type: "purchase_order", entity_key: "7", details: { line_count: 2 } };

function mockApi() {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const path = String(input);
    if (init?.method === "POST") return reply({ id: 99 }, 201);
    if (path.includes("/operations/summary")) return reply(summary);
    if (path.includes("/operations/orders/7")) return reply({ ...order, ordered_on: "2026-11-18", lead_time_days: 7, version: 1, note: "", supplier_id: 2, lines: [] });
    if (path.includes("/operations/orders")) return reply(page([order]));
    if (path.includes("/operations/audit")) return reply(page([audit]));
    if (path.includes("/operations/products")) return reply(page([product]));
    if (path.includes("/operations/suppliers")) return reply(page([supplier]));
    if (path.includes("/supplier-item-policies")) return reply(page([policy]));
    if (path.includes("/operations/product-filters")) return reply({ countries: ["Japan", "Korea"], suppliers: [{ id: 2, carrier: "Nhà mạng A" }] });
    if (path.includes("/dealers?")) return reply(page([{ id: 3, code: "DL-HN", name: "Đại lý HN", contact: "", active: true, version: 1 }]));
    return reply(page([]));
  });
}

afterEach(() => { cleanup(); vi.restoreAllMocks(); history.replaceState(null, "", "/"); });

it("opens a purchase order by clicking anywhere on its row", async () => {
  history.replaceState(null, "", "/#orders");
  mockApi(); render(<App />);
  fireEvent.click(await within(await screen.findByRole("region", { name: /^Đơn nhập/ })).findByText("2026-11-25"));
  await waitFor(() => expect(location.search).toContain("ops_order=7"));
});

it("shows audit details in a dialog that links to the purchase order", async () => {
  history.replaceState(null, "", "/#audit");
  mockApi(); render(<App />);
  fireEvent.click(await screen.findByText("Quản trị"));
  const dialog = await screen.findByRole("dialog", { name: "Tạo mới · Đơn nhập" });
  expect(within(dialog).getByText("Số dòng sản phẩm")).toBeVisible();
  fireEvent.click(within(dialog).getByRole("button", { name: "Mở đơn nhập" }));
  await waitFor(() => expect(location.search).toContain("ops_order=7"));
});

it("edits a product's lot and threshold as a new policy version", async () => {
  history.replaceState(null, "", "/#catalog");
  const fetch = mockApi(); render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Chính sách nhập" }));
  const dialog = await screen.findByRole("dialog", { name: "Chính sách nhập · SIM A" });
  expect(within(dialog).getByLabelText("Thời gian nhập (ngày)")).toHaveValue(5);
  await waitFor(() => expect(within(dialog).getByLabelText("Lượng nhập mỗi lần")).toHaveValue(20));
  fireEvent.change(within(dialog).getByLabelText("Lượng nhập mỗi lần"), { target: { value: "30" } });
  fireEvent.click(within(dialog).getByRole("button", { name: "Lưu cấu hình sản phẩm" }));
  await waitFor(() => expect(fetch.mock.calls.some(([p, i]) => String(p).includes("/supplier-item-policies") && i?.method === "POST")).toBe(true));
  const [, init] = fetch.mock.calls.find(([p, i]) => String(p).includes("/supplier-item-policies") && i?.method === "POST")!;
  expect(JSON.parse(String(init!.body))).toMatchObject({ item_id: 5, supplier_id: 2, expected_version: 2, fixed_order_qty: 30, configured_rop_floor: 4 });
});

it("creates a login for a dealer from the dealer list", async () => {
  history.replaceState(null, "", "/#dealers");
  const fetch = mockApi(); render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Cấp tài khoản" }));
  const dialog = await screen.findByRole("dialog", { name: "Cấp tài khoản · Đại lý HN" });
  fireEvent.change(within(dialog).getByLabelText("Mật khẩu"), { target: { value: "mat-khau-thu-12" } });
  fireEvent.click(within(dialog).getByRole("button", { name: "Tạo tài khoản" }));
  await waitFor(() => expect(fetch.mock.calls.some(([p, i]) => String(p).includes("/auth/users") && i?.method === "POST")).toBe(true));
  const [, init] = fetch.mock.calls.find(([p, i]) => String(p).includes("/auth/users") && i?.method === "POST")!;
  expect(JSON.parse(String(init!.body))).toMatchObject({ username: "dl-hn", role: "dealer", dealer_id: 3, display_name: "Đại lý HN" });
});

it("filters products and opens a supplier page listing its products", async () => {
  history.replaceState(null, "", "/#catalog");
  const fetch = mockApi(); render(<App />);
  fireEvent.change(await screen.findByLabelText("Quốc gia sử dụng"), { target: { value: "Japan" } });
  fireEvent.change(screen.getByLabelText("Trạng thái"), { target: { value: "inactive" } });
  await waitFor(() => expect(fetch.mock.calls.some(([p]) => String(p).includes("/operations/products?") && String(p).includes("country=Japan") && String(p).includes("active=false"))).toBe(true));
  fireEvent.click(screen.getByRole("button", { name: "Xóa bộ lọc" }));
  expect(screen.getByLabelText("Quốc gia sử dụng")).toHaveValue("");

  history.replaceState(null, "", "/#suppliers"); cleanup(); render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Xem chi tiết" }));
  await waitFor(() => expect(location.search).toContain("ops_supplier=2"));
  expect(await screen.findByRole("heading", { name: "Nhà mạng A" })).toBeVisible();
  expect(screen.getByText("40")).toBeVisible();
  await waitFor(() => expect(fetch.mock.calls.some(([p]) => String(p).includes("/operations/products?") && String(p).includes("supplier_id=2"))).toBe(true));
  fireEvent.click(await screen.findByRole("button", { name: "Chính sách nhập" }));
  expect(await screen.findByRole("dialog", { name: "Chính sách nhập · SIM A" })).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Đóng" }));
  fireEvent.click(screen.getByRole("button", { name: "← Tất cả nhà cung cấp" }));
  await waitFor(() => expect(location.search).not.toContain("ops_supplier"));
});

it("lists warehouses as cards and opens one warehouse's balances", async () => {
  history.replaceState(null, "", "/#stock");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const path = String(input);
    if (path.includes("/operations/summary")) return reply(summary);
    if (path.includes("/operations/warehouses")) return reply(page([{ id: 4, code: "HCM", name: "Kho HCM", country: "Việt Nam", active: true, version: 1, stocked_items: 3, empty_items: 1, on_hand_qty: 25, incoming_qty: 8 }]));
    if (path.includes("/operations/stock")) return reply(page([{ warehouse_id: 4, item_id: 2, sku: "SIM-A", name: "SIM A", warehouse: "Kho HCM", on_hand_qty: 5, version: 1 }]));
    return reply(page([]));
  });
  render(<App />);
  const card = await screen.findByRole("button", { name: "Mở kho Kho HCM tại Việt Nam" });
  expect(within(card).getByText("1 mặt hàng đã hết")).toBeVisible();
  expect(fetch.mock.calls.some(([p]) => String(p).includes("/operations/stock?"))).toBe(false);
  fireEvent.click(card);
  await waitFor(() => expect(location.search).toContain("ops_warehouse=4"));
  expect(await screen.findByRole("heading", { name: "Sản phẩm tại Kho HCM" })).toBeVisible();
  await waitFor(() => expect(fetch.mock.calls.some(([p]) => String(p).includes("/operations/stock?") && String(p).includes("warehouse_id=4"))).toBe(true));
  fireEvent.click(screen.getByRole("button", { name: /Danh sách kho/ }));
  await waitFor(() => expect(location.search).not.toContain("ops_warehouse"));
});
