import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Operations } from "../src/pages/Operations";
import { OrderEditor } from "../src/operations/OrderEditor";
import { ReceiptEditor } from "../src/operations/ReceiptEditor";
import { OrderDetail } from "../src/operations/OrderDetail";
import { MovementEditor } from "../src/operations/MovementEditor";
import { useOperationWrite } from "../src/operations/useOperationWrite";
import { navigationUrl, readContext, readPage } from "../src/utils/url";
import type { Context } from "../src/types/context";
import type { Order } from "../src/operations/types";

const warehouse = { id: 1, name: "Kho HCM", country: "Việt Nam", code: "HCM", active: true, version: 1 };
const supplier = { id: 1, carrier: "Nhà mạng A", lead_time_days: 30, version: 1 };
const product = { id: 2, name: "SIM du lịch", sku: "SIM-01", product_type: "physical_SIM", carrier: "Nhà mạng A", supplier_id: 1, destination_country: "Nhật", active: true, version: 1 };
const order: Order = { id: 3, number: "PO-03", status: "ordered", supplier_id: 1, carrier: "Nhà mạng A", ordered_on: "2026-11-01", eta: "2026-12-01", lead_time_days: 30, version: 2, note: "", lines: [{ id: 10, item_id: 2, warehouse_id: 1, name: "SIM du lịch", sku: "SIM-01", warehouse: "Kho HCM", ordered_qty: 10, received_qty: 4, remaining_qty: 6 }] };
const page = (items: unknown[]) => ({ items, total: items.length, page: 1, page_size: 25 });
const reply = (value: unknown, status = 200) => ({ ok: status < 400, status, json: async () => value }) as Response;
const context: Context = { runId: "", warehouseId: "", itemId: "", supplierId: "", productType: "", origin: "", opsTab: "stock" };
afterEach(() => { cleanup(); vi.restoreAllMocks(); history.replaceState(null, "", "/"); });

it("isolates operational navigation from legacy forecast context", () => {
  expect(navigationUrl({ ...context, runId: "old", origin: "2025-01-01", opsOrderId: "3" }, "orders", "history")).toBe("?ops_order=3#orders");
  expect(navigationUrl({ ...context, runId: "old", opsOrderId: "3" }, "stock", "history")).toBe("?#stock");
  history.replaceState(null, "", "/?ops_order=3#orders");
  expect(readPage()).toBe("orders");
  expect(readContext()).toMatchObject({ opsOrderId: "3", runId: "" });
  // Links saved before the split still open the matching page.
  history.replaceState(null, "", "/?ops_tab=products#operations");
  expect(readPage()).toBe("catalog");
  history.replaceState(null, "", "/");
  expect(readPage()).toBe("dashboard");
  history.replaceState(null, "", "/?run_id=plan-a");
  expect(readPage()).toBe("overview");
});

it("shows a truthful empty ledger and offers setup without inventing stock", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (path) => String(path).includes("/summary") ? reply({ business_date: "2026-11-15", on_hand_units: 0, pending_orders: 0, draft_orders: 0, documents_today: 0 }) : reply(page([])));
  render(<Operations ctx={context} onContext={vi.fn()} />);
  expect(await screen.findByText(/Chưa có số dư phù hợp/)).toBeVisible();
  expect(screen.getByRole("button", { name: "Kiểm kê / tồn đầu" })).toBeDisabled();
  expect(fetch.mock.calls.every(([path]) => !String(path).includes("/runs"))).toBe(true);
});

it("creates a real draft with selected supplier, product and warehouse", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (path, options) => options?.method === "POST" ? reply({ ...order, status: "draft" }, 201) : reply(page(String(path).includes("products") ? [product] : [])));
  const saved = vi.fn();
  render(<OrderEditor suppliers={[supplier]} warehouses={[warehouse]} today="2026-11-15" onClose={vi.fn()} onSaved={saved} />);
  fireEvent.change(screen.getByLabelText("Nhà cung cấp"), { target: { value: "1" } });
  fireEvent.click(await screen.findByRole("button", { name: "Chọn" }));
  fireEvent.change(screen.getByLabelText("Số lượng SIM-01"), { target: { value: "12" } });
  fireEvent.click(screen.getByRole("button", { name: "Lưu nháp" }));
  await waitFor(() => expect(saved).toHaveBeenCalledOnce());
  const request = fetch.mock.calls.find(([, options]) => options?.method === "POST")!;
  expect(String(request[0])).toMatch(/\/operations\/orders$/);
  expect(JSON.parse(String(request[1]?.body))).toMatchObject({ supplier_id: 1, lines: [{ item_id: 2, warehouse_id: 1, quantity: 12 }] });
  expect(new Headers(request[1]?.headers).get("Idempotency-Key")).toBeTruthy();
});

it("receives only actual partial quantity and keeps order version", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(reply({ id: "receipt" }, 201)), saved = vi.fn();
  render(<ReceiptEditor order={order} today="2026-11-15" onClose={vi.fn()} onSaved={saved} />);
  fireEvent.change(screen.getByLabelText("Thực nhận SIM-01"), { target: { value: "2" } });
  fireEvent.change(screen.getByLabelText("Mã phiếu giao hàng"), { target: { value: "DELIVERY-02" } });
  fireEvent.click(screen.getByRole("button", { name: "Ghi nhận nhập kho" }));
  await waitFor(() => expect(saved).toHaveBeenCalledOnce());
  expect(JSON.parse(String(fetch.mock.calls[0][1]?.body))).toMatchObject({ expected_version: 2, lines: [{ order_line_id: 10, quantity: 2 }], external_ref: "DELIVERY-02" });
});

it("accepts a physical count of zero with the fresh balance version", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (_, options) => options?.method === "POST" ? reply({ id: "count" }, 201) : reply({ warehouse_id: 1, item_id: 2, name: "SIM du lịch", on_hand_qty: 8, version: 7 }));
  const close = vi.fn();
  render(<MovementEditor kind="count" initial={{ warehouse_id: 1, item_id: 2, warehouse: "Kho HCM", name: "SIM", on_hand_qty: 5, version: 1 }} warehouses={[warehouse]} today="2026-11-15" onClose={close} />);
  expect(await screen.findByText("8")).toBeVisible();
  fireEvent.change(screen.getByLabelText("Số lượng đếm thực tế"), { target: { value: "0" } });
  fireEvent.change(screen.getByLabelText("Mã phiếu đối chiếu"), { target: { value: "COUNT-02" } });
  fireEvent.change(screen.getByLabelText("Lý do điều chỉnh"), { target: { value: "Kiểm đếm thực tế" } });
  fireEvent.click(screen.getByRole("button", { name: "Ghi sổ" }));
  await waitFor(() => expect(close).toHaveBeenCalledOnce());
  const request = fetch.mock.calls.find(([, options]) => options?.method === "POST")!;
  expect(JSON.parse(String(request[1]?.body))).toMatchObject({ quantity: 0, expected_balance_version: 7 });
});

it("keeps failed receipt fields for a safe retry with the same request key", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("Mất kết nối")).mockResolvedValue(reply({ id: "receipt" }, 201));
  render(<ReceiptEditor order={order} today="2026-11-15" onClose={vi.fn()} onSaved={vi.fn()} />);
  fireEvent.change(screen.getByLabelText("Mã phiếu giao hàng"), { target: { value: "REF-RETRY" } });
  fireEvent.click(screen.getByRole("button", { name: "Ghi nhận nhập kho" }));
  expect(await screen.findByText("Mất kết nối")).toBeVisible();
  expect(screen.getByLabelText("Mã phiếu giao hàng")).toHaveValue("REF-RETRY");
  fireEvent.click(screen.getByRole("button", { name: "Ghi nhận nhập kho" }));
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  expect(new Headers(fetch.mock.calls[0][1]?.headers).get("Idempotency-Key")).toBe(new Headers(fetch.mock.calls[1][1]?.headers).get("Idempotency-Key"));
});

it("displays posted documents as read-only details", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (path) => {
    const url = String(path);
    if (url.endsWith("/documents/doc-1")) return reply({ id: "doc-1", number: "WH-001", kind: "receipt", occurred_on: "2026-11-15", external_ref: "REF-1", lines: [{ sku: "SIM-01", warehouse: "Kho HCM", quantity_delta: 4, balance_after: 4 }] });
    return reply(page(url.includes("/documents?") ? [{ id: "doc-1", number: "WH-001", kind: "receipt" }] : []));
  });
  render(<Operations ctx={{ ...context, opsTab: "documents" }} onContext={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: "WH-001" }));
  const dialog = await screen.findByRole("dialog");
  expect(await within(dialog).findByText("SIM-01")).toBeVisible();
  expect(within(dialog).queryByRole("button", { name: /Xóa|Sửa/ })).toBeNull();
});

it("prevents duplicate writes even within the same event before rerender", async () => {
  let finish!: (response: Response) => void;
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
  function Harness() { const write = useOperationWrite(); return <button onClick={() => { void write.send("/counts", {}); void write.send("/counts", {}); }}>Ghi</button>; }
  render(<Harness />); fireEvent.click(screen.getByRole("button", { name: "Ghi" }));
  expect(fetch).toHaveBeenCalledOnce(); finish(reply({ id: 1 }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Ghi" })).toBeVisible());
});

it("background refresh preserves a receipt draft and never advances its expected version", async () => {
  let reads = 0;
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (_, options) => options?.method === "POST"
    ? reply({ error: { code: "version_conflict", message: "Changed" } }, 409)
    : reply({ ...order, version: ++reads === 1 ? 2 : 9 }));
  render(<OrderDetail id="3" today="2026-11-15" suppliers={[supplier]} warehouses={[warehouse]} onBack={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: "Nhận hàng" }));
  fireEvent.change(screen.getByLabelText("Mã phiếu giao hàng"), { target: { value: "PRESERVE-REF" } });
  await act(async () => { window.dispatchEvent(new Event("sigma:refresh")); });
  await waitFor(() => expect(reads).toBe(2));
  expect(screen.getByLabelText("Mã phiếu giao hàng")).toHaveValue("PRESERVE-REF");
  fireEvent.click(screen.getByRole("button", { name: "Ghi nhận nhập kho" }));
  expect(await screen.findByText(/Dữ liệu đã được người khác cập nhật/)).toBeVisible();
  const request = fetch.mock.calls.find(([, options]) => options?.method === "POST")!;
  expect(JSON.parse(String(request[1]?.body)).expected_version).toBe(2);
  expect(screen.getByLabelText("Mã phiếu giao hàng")).toHaveValue("PRESERVE-REF");
  expect(within(screen.getByRole("dialog")).queryByRole("button", { name: "Thử tải lại" })).toBeNull();
});

it("moves the ETA of a confirmed order with a reason and shows the planned date", async () => {
  let current: Order = { ...order, planned_eta: order.eta };
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (_, options) => {
    if (options?.method === "POST") current = { ...current, eta: "2026-12-20", version: current.version + 1 };
    return reply(current);
  });
  render(<OrderDetail id="3" today="2026-11-16" suppliers={[supplier]} warehouses={[warehouse]} onBack={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: "Đổi ngày dự kiến" }));
  const date = screen.getByLabelText("Ngày dự kiến mới");
  expect(date).toHaveAttribute("min", "2026-11-16");
  fireEvent.change(date, { target: { value: "2026-12-20" } });
  fireEvent.change(screen.getByLabelText("Lý do điều chỉnh"), { target: { value: "Nhà mạng báo chậm giao" } });
  fireEvent.click(screen.getByRole("button", { name: "Lưu ngày mới" }));
  await waitFor(() => expect(fetch.mock.calls.some(([, o]) => o?.method === "POST")).toBe(true));
  const [path, options] = fetch.mock.calls.find(([, o]) => o?.method === "POST")!;
  expect(String(path)).toMatch(/\/operations\/orders\/3\/eta$/);
  expect(JSON.parse(String(options?.body))).toEqual({ expected_version: 2, eta: "2026-12-20", reason: "Nhà mạng báo chậm giao" });
  expect(await screen.findByText("Ban đầu 2026-12-01 · đã điều chỉnh")).toBeVisible();
});

it("shows how many products a supplier lead time reaches", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (path) => String(path).includes("/summary")
    ? reply({ business_date: "2026-11-16" }) : reply(page(String(path).includes("/operations/suppliers") ? [{ ...supplier, lead_time_days: 10, product_count: 12 }] : [])));
  render(<Operations ctx={{ ...context, opsTab: "suppliers" }} onContext={vi.fn()} />);
  expect(await screen.findByText("10 ngày")).toBeVisible();
  expect(screen.getByText("12")).toBeVisible();
  expect(screen.getByText(/áp dụng cho mọi sản phẩm của nhà cung cấp đó/)).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Đổi thời gian nhập" }));
  expect(await screen.findByText(/Áp dụng cho 12 sản phẩm/)).toBeVisible();
});
