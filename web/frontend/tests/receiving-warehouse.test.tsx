import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ProductReceivingForm } from "../src/components/products/ProductReceivingForm";
import { resultQuery, contextUrl, readContext } from "../src/utils/url";
import type { Context } from "../src/types/context";

const warehouse = { id: 1, city: "Source City", destination_country: "Source Market" };
const target = { id: 201, city: "Receiving City", destination_country: "Receiving Market" };
const product = { id: 7, warehouse_id: 1, receiving_warehouse_id: 1, receiving_version: 0,
  receiving_source: "inherited", receiving_schema_ready: true, warehouse, receiving_warehouse: warehouse };
const reply = (data: unknown, status = 200) => Promise.resolve({ ok: status === 200, status, json: async () => data } as Response);

afterEach(() => { cleanup(); vi.restoreAllMocks(); history.replaceState(null, "", "/"); });

it("loads every warehouse page and saves only the product default", async () => {
  const saved = vi.fn(), writes: unknown[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation((input, options) => {
    const url = new URL(String(input), "http://localhost");
    if (options?.method === "PATCH") { writes.push(JSON.parse(String(options.body))); return reply({ receiving_version: 1 }); }
    return reply({ total: 101, items: url.searchParams.get("page") === "2" ? [target]
      : Array.from({ length: 100 }, (_, index) => ({ ...warehouse, id: index + 1, city: `City ${index + 1}` })) });
  });
  render(<ProductReceivingForm product={product} onSaved={saved} onReload={vi.fn()} />);
  await screen.findByRole("option", { name: "Receiving City · Receiving Market" });
  fireEvent.change(screen.getByLabelText("Kho nhận hàng mặc định"), { target: { value: "201" } });
  fireEvent.click(screen.getByRole("button", { name: "Lưu kho nhận" }));
  await waitFor(() => expect(saved).toHaveBeenCalledOnce());
  expect(writes).toEqual([{ receiving_warehouse_id: 201, expected_version: 0 }]);
  expect(vi.mocked(fetch).mock.calls.every(([, options]) => options?.method !== "POST")).toBe(true);
});

it("retains the chosen warehouse after a conflict and requires an explicit reload", async () => {
  const reload = vi.fn();
  vi.spyOn(globalThis, "fetch").mockImplementation((_input, options) => options?.method === "PATCH"
    ? reply({ error: { code: "version_conflict", message: "Changed" } }, 409)
    : reply({ total: 2, items: [warehouse, target] }));
  render(<ProductReceivingForm product={product} onSaved={vi.fn()} onReload={reload} />);
  await screen.findByRole("option", { name: "Receiving City · Receiving Market" });
  fireEvent.change(screen.getByLabelText("Kho nhận hàng mặc định"), { target: { value: "201" } });
  fireEvent.click(screen.getByRole("button", { name: "Lưu kho nhận" }));
  await screen.findByRole("alert");
  expect(screen.getByLabelText("Kho nhận hàng mặc định")).toHaveValue("201");
  expect(screen.getByRole("button", { name: "Lưu kho nhận" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Tải lại kho đã lưu" }));
  expect(reload).toHaveBeenCalledOnce();
});

it("preserves the receiving scope in the URL without sending it as a source filter", () => {
  const ctx: Context = { runId: "run", warehouseId: "201", warehouseScope: "receiving", itemId: "7", supplierId: "", productType: "", origin: "2025-10-31" };
  const query = new URLSearchParams(resultQuery(ctx));
  expect(query.get("receiving_warehouse_id")).toBe("201");
  expect(query.has("warehouse_id")).toBe(false);
  history.replaceState(null, "", `?${contextUrl(ctx)}#inventory`);
  expect(readContext()).toEqual(ctx);
});
