import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import App from "../src/App";

const reply = (value: unknown) => ({ ok: true, status: 200, json: async () => value }) as Response;
const page = (items: unknown[]) => ({ items, total: items.length, page: 1, page_size: 25 });
const summary = { business_date: "2026-11-16", on_hand_units: 42, pending_orders: 2, late_orders: 1, draft_orders: 0, stocked_items: 3, documents_today: 4 };
const orders = [
  { id: 7, number: "PO-07", carrier: "Nhà mạng A", eta: "2026-11-10", status: "ordered", ordered_qty: 10, received_qty: 0 },
  { id: 8, number: "PO-08", carrier: "Nhà mạng B", eta: "2026-11-20", status: "partially_received", ordered_qty: 5, received_qty: 2 },
];

function mockApi() {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const path = String(input);
    if (path.includes("/operations/summary")) return reply(summary);
    if (path.includes("/operations/orders/7")) return reply({ ...orders[0], ordered_on: "2026-11-01", lead_time_days: 9, version: 1, note: "", supplier_id: 1, lines: [] });
    if (path.includes("/operations/orders")) return reply(page(orders));
    if (path.includes("/operations/stock")) return reply(page([{ warehouse_id: 1, item_id: 2, sku: "SIM-LOW", name: "SIM sắp hết", warehouse: "Kho HCM", on_hand_qty: 1 }]));
    return reply(page([]));
  });
}

afterEach(() => { cleanup(); vi.restoreAllMocks(); history.replaceState(null, "", "/"); });

it("opens the management dashboard by default without loading scenario runs", async () => {
  const fetch = mockApi();
  render(<App />);
  expect(await screen.findByRole("heading", { name: "Tổng quan" })).toBeVisible();
  expect(await screen.findByText("SIM-LOW")).toBeVisible();
  expect(screen.getByText("2026-11-10 · trễ")).toBeVisible();
  expect(screen.getByText("2026-11-20")).toBeVisible();
  expect(String(fetch.mock.calls.find(([p]) => String(p).includes("/operations/orders"))![0])).toContain("status=open&sort=eta");
  expect(fetch.mock.calls.some(([p]) => String(p).includes("/runs"))).toBe(false);
  expect(screen.queryByRole("button", { name: "Tạo phương án" })).toBeNull();
  expect(screen.queryByText("Dữ liệu mô phỏng")).toBeNull();
  const nav = screen.getByRole("navigation", { name: "Điều hướng chính" });
  for (const group of ["KHO", "NHẬP HÀNG", "DANH MỤC", "HỆ THỐNG", "CÔNG CỤ"]) expect(within(nav).getByText(group)).toBeVisible();
});

it("opens an order from the dashboard and returns to the list from the menu", async () => {
  mockApi();
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "PO-07" }));
  await waitFor(() => expect(location.hash).toBe("#orders"));
  expect(location.search).toContain("ops_order=7");
  fireEvent.click(within(screen.getByRole("navigation", { name: "Điều hướng chính" })).getByRole("button", { name: "Đơn nhập" }));
  await waitFor(() => expect(location.search).not.toContain("ops_order"));
  expect(await screen.findByRole("heading", { name: "Đơn nhập" })).toBeVisible();
});

it("keeps forecast and scenarios inside one Tools entry", async () => {
  const fetch = mockApi();
  render(<App />);
  const nav = await screen.findByRole("navigation", { name: "Điều hướng chính" });
  fireEvent.click(within(nav).getByRole("button", { name: "Dự báo & kịch bản" }));
  const tools = await screen.findByRole("navigation", { name: "Công cụ dự báo" });
  expect(within(tools).getByRole("button", { name: "Dự báo" })).toHaveAttribute("aria-current", "page");
  expect(within(nav).getByRole("button", { name: "Dự báo & kịch bản" })).toHaveAttribute("aria-current", "page");
  fireEvent.click(within(tools).getByRole("button", { name: "Kịch bản" }));
  await waitFor(() => expect(location.hash).toBe("#scenarios"));
  expect(within(nav).getByRole("button", { name: "Dự báo & kịch bản" })).toHaveAttribute("aria-current", "page");
  await waitFor(() => expect(fetch.mock.calls.some(([p]) => String(p).includes("/runs"))).toBe(true));
});
