import { useState } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { DetailDrawer } from "../src/components/ui/DetailDrawer";
import { ExportButton } from "../src/components/ui/ExportButton";
import { Pager } from "../src/components/ui/Pager";
import { Table } from "../src/components/ui/Table";
import { resultQuery } from "../src/utils/url";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it("keeps table rows operable with Enter and Space", () => {
  const selected = vi.fn();
  const row = { id: 1, sku: "SYNTHETIC-SKU" };
  render(<Table rows={[row]} columns={[{ key: "sku", label: "SKU" }]} onRow={selected} />);
  const target = screen.getByText(row.sku).closest("tr")!;
  expect(target).toHaveAttribute("tabindex", "0");
  fireEvent.keyDown(target, { key: "Enter" });
  fireEvent.keyDown(target, { key: " " });
  expect(selected.mock.calls).toEqual([[row], [row]]);
});

it("keeps pager limits at 50 rows and requests the adjacent page", () => {
  const change = vi.fn();
  const view = render(<Pager page={1} total={50} onChange={change} />);
  expect(screen.getByRole("button", { name: "← Trước" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Sau →" })).toBeDisabled();
  view.rerender(<Pager page={1} total={51} onChange={change} />);
  fireEvent.click(screen.getByRole("button", { name: "Sau →" }));
  expect(change).toHaveBeenLastCalledWith(2);
  view.rerender(<Pager page={2} total={51} onChange={change} />);
  expect(screen.getByRole("button", { name: "Sau →" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "← Trước" }));
  expect(change).toHaveBeenLastCalledWith(1);
});

it("exports the selected dataset and filters through the same API prefix", () => {
  const filters = resultQuery({ runId: "synthetic", warehouseId: "18", itemId: "4", productType: "eSIM", supplierId: "", origin: "2025-10-31" }, { as_of_date: "2025-10-31" });
  render(<ExportButton url={`/runs/synthetic/exports/inventory_daily?${filters}`} />);
  const link = screen.getByRole("link", { name: /Xuất CSV/ });
  const url = new URL(link.getAttribute("href")!, "http://localhost");
  expect(url.pathname).toBe("/api/v1/runs/synthetic/exports/inventory_daily");
  expect(Object.fromEntries(url.searchParams)).toEqual({ warehouse_id: "18", item_id: "4", product_type: "eSIM", as_of_date: "2025-10-31" });
  expect(link).toHaveAttribute("download");
});

it("traps drawer focus, closes with Escape and restores its trigger", () => {
  // jsdom has no layout; expose the same visible controls a browser sees.
  vi.spyOn(HTMLElement.prototype, "getClientRects").mockReturnValue([new DOMRect(0, 0, 10, 10)] as unknown as DOMRectList);
  function Example() {
    const [open, setOpen] = useState(false);
    return <><button onClick={() => setOpen(true)}>Mở chi tiết</button>{open && <DetailDrawer title="Synthetic item" onClose={() => setOpen(false)}><button>Hành động cuối</button></DetailDrawer>}</>;
  }
  render(<Example />);
  const trigger = screen.getByRole("button", { name: "Mở chi tiết" });
  trigger.focus();
  fireEvent.click(trigger);
  const first = screen.getByRole("button", { name: "Đóng chi tiết" });
  expect(first).toHaveFocus();
  fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
  expect(screen.getByRole("button", { name: "Hành động cuối" })).toHaveFocus();
  fireEvent.keyDown(document, { key: "Tab" });
  expect(first).toHaveFocus();
  fireEvent.keyDown(document, { key: "Escape" });
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(trigger).toHaveFocus();
});
