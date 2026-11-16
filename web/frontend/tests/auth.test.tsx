import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { SessionBoundary, AccountMenu } from "../src/auth/SessionBoundary";
import { api, setCsrfToken } from "../src/services/http";

afterEach(() => { cleanup(); vi.restoreAllMocks(); setCsrfToken(""); });
const admin = { id: 1, username: "admin", display_name: "Quản trị", role: "admin", dealer_id: null, active: true };
const reply = (data: unknown, status = 200) => ({ ok: status === 200, status, json: async () => data }) as Response;

it("fails closed while session lookup fails", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("offline"));
  render(<SessionBoundary><span>Private workspace</span></SessionBoundary>);
  expect(await screen.findByText("Không kết nối được hệ thống")).toBeVisible();
  expect(screen.queryByText("Private workspace")).toBeNull();
});

it("logs in, attaches CSRF only to mutations and logs out", async () => {
  const calls: { path: string; options?: RequestInit }[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (path, options) => {
    calls.push({ path: String(path), options });
    if (String(path).endsWith("/auth/session")) return reply({ error: { message: "Login" } }, 401);
    if (String(path).endsWith("/auth/login")) return reply({ required: true, user: admin, csrf_token: "synthetic-csrf" });
    return reply({ ok: true });
  });
  render(<SessionBoundary><span>Private workspace</span><AccountMenu /></SessionBoundary>);
  fireEvent.change(await screen.findByLabelText("Tên đăng nhập"), { target: { value: "admin" } });
  fireEvent.change(screen.getByLabelText("Mật khẩu"), { target: { value: "synthetic-password" } });
  fireEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));
  expect(await screen.findByText("Private workspace")).toBeVisible();
  fireEvent.click(screen.getByLabelText("Mở tài khoản"));
  fireEvent.click(screen.getByRole("button", { name: "Đăng xuất" }));
  expect(await screen.findByLabelText("Tên đăng nhập")).toBeVisible();
  const logout = calls.find((call) => call.path.endsWith("/auth/logout"))!;
  expect(new Headers(logout.options?.headers).get("X-CSRF-Token")).toBe("synthetic-csrf");
  expect(logout.options?.credentials).toBe("include");
  expect(new Headers(calls[0].options?.headers).has("X-CSRF-Token")).toBe(false);
});

it("dealer sees own portal without mounting admin workspace", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (path) => String(path).endsWith("/auth/session")
    ? reply({ required: true, user: { ...admin, role: "dealer", dealer_id: 2 }, csrf_token: "synthetic" })
    : reply({ items: [{ item_id: 1, sku: "OWN-SKU", name: "SIM", product_type: "eSIM", available_qty: 5 }], total: 1, page: 1, page_size: 25 }));
  render(<SessionBoundary><span>Private workspace</span></SessionBoundary>);
  expect(await screen.findByText("SIGMA · Cổng đại lý")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Đặt hàng" }));
  expect(await screen.findByText("OWN-SKU")).toBeVisible();
  expect(screen.queryByText("Private workspace")).toBeNull();
  expect(screen.queryByRole("button", { name: "Tài khoản" })).toBeNull();
});

it("removes the private app on API expiry and permits legacy mode only explicitly", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(reply({ required: true, user: admin, csrf_token: "token" }));
  const view = render(<SessionBoundary><span>Private workspace</span></SessionBoundary>);
  expect(await screen.findByText("Private workspace")).toBeVisible();
  fetch.mockResolvedValue(reply({ error: { code: "authentication_required" } }, 401));
  await expect(api("/products")).rejects.toThrow();
  await waitFor(() => expect(screen.queryByText("Private workspace")).toBeNull());
  view.unmount();
  fetch.mockResolvedValue(reply({ required: false, user: null }));
  render(<SessionBoundary><span>Legacy test workspace</span></SessionBoundary>);
  expect(await screen.findByText("Legacy test workspace")).toBeVisible();
});
