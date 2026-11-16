import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { DealerPortal } from "../src/dealers/DealerPortal";
import { DealerRequestsPage } from "../src/pages/Dealers";

const reply = (value: unknown, status = 200) => ({ ok: status < 400, status, json: async () => value }) as Response;
const page = (items: unknown[]) => ({ items, total: items.length, page: 1, page_size: 25 });
const request = { id: 5, number: "DR-1", status: "submitted", version: 1, note: "", reject_reason: null, dealer_code: "DL-A", dealer_name: "Đại lý A",
  created_at: "2026-11-16T03:00:00Z", received_at: null, lines: [{ item_id: 2, sku: "SIM-01", name: "SIM du lịch", quantity: 3 }] };

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it("dealer submits only the products with a quantity", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (path, options) => options?.method === "POST"
    ? reply(request, 201) : reply(page(String(path).includes("/dealer/products")
      ? [{ item_id: 2, sku: "SIM-01", name: "SIM du lịch", product_type: "eSIM", available_qty: 9 }, { item_id: 3, sku: "SIM-02", name: "Khác", product_type: "eSIM", available_qty: 1 }] : [])));
  render(<DealerPortal />);
  fireEvent.click(screen.getByRole("button", { name: "Đặt hàng" }));
  const submit = screen.getByRole("button", { name: "Gửi yêu cầu" });
  expect(submit).toBeDisabled();
  fireEvent.change(await screen.findByLabelText("Số lượng SIM-01"), { target: { value: "3" } });
  fireEvent.click(submit);
  await waitFor(() => expect(fetch.mock.calls.some(([, o]) => o?.method === "POST")).toBe(true));
  const [path, options] = fetch.mock.calls.find(([, o]) => o?.method === "POST")!;
  expect(String(path)).toMatch(/\/dealer\/requests$/);
  expect(JSON.parse(String(options?.body))).toEqual({ note: "", lines: [{ item_id: 2, quantity: 3 }] });
  expect(new Headers(options?.headers).get("Idempotency-Key")).toBeTruthy();
  expect(await screen.findByRole("heading", { name: "Yêu cầu của tôi" })).toBeVisible();
});

it("admin approves then issues from a chosen warehouse on the business date", async () => {
  let current = { ...request };
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, options) => {
    const path = String(input);
    if (options?.method === "POST") { current = { ...current, status: path.endsWith("/approve") ? "approved" : "issued", version: current.version + 1 }; return reply(current); }
    if (path.includes("/dealers/requests/5")) return reply(current);
    if (path.includes("/dealers/requests")) return reply(page([{ ...current, quantity: 3, line_count: 1 }]));
    if (path.includes("/operations/warehouses")) return reply(page([{ id: 4, name: "Kho HCM", code: "HCM", country: "VN", active: true, version: 1 }]));
    if (path.includes("/operations/summary")) return reply({ business_date: "2026-11-16" });
    return reply(page([]));
  });
  render(<DealerRequestsPage />);
  fireEvent.click(await screen.findByRole("button", { name: "DR-1" }));
  fireEvent.click(await screen.findByRole("button", { name: "Duyệt" }));
  await waitFor(() => expect(fetch.mock.calls.some(([p]) => String(p).endsWith("/requests/5/approve"))).toBe(true));
  fireEvent.click(await screen.findByRole("button", { name: "DR-1" }));
  fireEvent.click(await screen.findByRole("button", { name: "Xuất kho" }));
  const issue = screen.getByRole("button", { name: "Xuất kho" });
  expect(issue).toBeDisabled();
  fireEvent.change(await screen.findByLabelText("Xuất từ kho"), { target: { value: "4" } });
  await waitFor(() => expect(issue).toBeEnabled());
  fireEvent.click(issue);
  await waitFor(() => expect(fetch.mock.calls.some(([p]) => String(p).endsWith("/requests/5/issue"))).toBe(true));
  const [, options] = fetch.mock.calls.find(([p]) => String(p).endsWith("/requests/5/issue"))!;
  expect(JSON.parse(String(options?.body))).toEqual({ expected_version: 2, warehouse_id: 4, occurred_on: "2026-11-16" });
});
