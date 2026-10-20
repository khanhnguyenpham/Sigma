import {
  cleanup,
  render,
  screen,
  fireEvent,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Overview } from "../src/pages/Overview";
import { Inventory } from "../src/pages/Inventory";
import { Replenishment } from "../src/pages/Replenishment";
import { RunDialog } from "../src/components/RunDialog";
import { type Run, type Context } from "../src/api/client";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
const ctx: Context = {
  runId: "old",
  origin: "2025-10-31",
  warehouseId: "",
  itemId: "",
  supplierId: "",
  productType: "",
};
const run = (id = "old") =>
  ({
    id,
    kind: "stock_projection",
    status: "complete",
    result_summary: {},
    as_of_date: "2025-10-31",
  }) as Run;
const response = (data: unknown) =>
  Promise.resolve({ ok: true, json: async () => data } as Response);
const workspace = {
  context: { run_id: "old", known_orders_through: "2025-10-31" },
  summary: {
    inventory_available: true,
    item_count: 1,
    on_hand_units: 7,
    replenish_items: 1,
    recommended_units: 14,
    incoming_lots: 0,
    pending_units: 0,
    urgent_items: 1,
  },
  attention: [
    {
      item_id: 1,
      warehouse_id: 18,
      sku: "TEST-SKU",
      carrier: "Demo",
      product_type: "eSIM",
      closing_qty: 7,
      rop: 20,
      recommended_qty: 14,
    },
  ],
  incoming: [],
  route_stock: [],
};

it("leads with real inventory actions and keeps processing history collapsed", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(() => response(workspace));
  const navigate = vi.fn(),
    open = vi.fn();
  render(
    <Overview
      run={run()}
      ctx={ctx}
      runs={[run()]}
      onRun={() => {}}
      onCreate={() => {}}
      onNavigate={navigate}
      onItem={open}
    />,
  );
  await screen.findByText("TEST-SKU");
  expect(screen.getByText("Tồn hiện có").closest("article")).toHaveTextContent(
    "7",
  );
  expect(
    screen
      .getAllByText("Cần bổ sung")
      .find((node) => node.closest("article"))
      ?.closest("article"),
  ).toHaveTextContent("1");
  expect(screen.queryByText(/R05|MAPE/)).toBeNull();
  fireEvent.click(screen.getByText("TEST-SKU"));
  expect(open).toHaveBeenCalledWith(workspace.attention[0], "inventory");
  fireEvent.click(screen.getByRole("button", { name: "Xem tất cả" }));
  expect(navigate).toHaveBeenCalledWith("replenishment");
  expect(screen.getByText("Các phương án gần đây")).not.toBeVisible();
});

it("clears operational totals immediately when the selected plan changes", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((url) =>
    String(url).includes("/old/") ? response(workspace) : new Promise(() => {}),
  );
  const props = {
    ctx,
    runs: [run()],
    onRun: () => {},
    onCreate: () => {},
    onNavigate: () => {},
    onItem: () => {},
  };
  const view = render(<Overview {...props} run={run()} />);
  await screen.findByText("TEST-SKU");
  view.rerender(
    <Overview {...props} run={run("new")} ctx={{ ...ctx, runId: "new" }} />,
  );
  expect(screen.queryByText("TEST-SKU")).toBeNull();
  expect(screen.getByText("Tồn hiện có").closest("article")).toHaveTextContent(
    "—",
  );
});

it("closes item details on context change before any old result can be reused", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation((url) =>
    String(url).includes("/new/")
      ? new Promise(() => {})
      : response(
          String(url).includes("/workspace")
            ? workspace
            : { items: workspace.attention, total: 1 },
        ),
  );
  const view = render(<Inventory run={run()} ctx={ctx} />);
  fireEvent.click(await screen.findByText("TEST-SKU"));
  expect(screen.getByRole("dialog")).toBeVisible();
  view.rerender(<Inventory run={run("new")} ctx={{ ...ctx, runId: "new" }} />);
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(screen.queryByText("TEST-SKU")).toBeNull();
});

it("resets replenishment pagination when the warehouse changes", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(() =>
      response({ items: [{ sku: "TEST-SKU" }], total: 120 }),
    );
  const view = render(<Replenishment run={run()} ctx={ctx} />);
  await screen.findByText("TEST-SKU");
  fireEvent.click(screen.getByRole("button", { name: "Sau →" }));
  await waitFor(() =>
    expect(fetch.mock.calls.some(([u]) => String(u).includes("page=2"))).toBe(
      true,
    ),
  );
  view.rerender(
    <Replenishment run={run()} ctx={{ ...ctx, warehouseId: "18" }} />,
  );
  await waitFor(() =>
    expect(String(fetch.mock.calls.at(-1)?.[0])).toContain("page=1"),
  );
  expect(String(fetch.mock.calls.at(-1)?.[0])).toContain("warehouse_id=18");
});

it("prefers the full replay parent rather than the newest future-only forecast", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(() =>
    response({ items: [{ id: 1, name: "Base", version: 1 }], total: 1 }),
  );
  const future = {
    ...run("future"),
    kind: "forecast",
    source_import_run_id: "source",
    as_of_date: "2025-12-31",
    result_summary: { origins: 1 },
  } as Run;
  const replay = {
    ...future,
    id: "replay",
    result_summary: { origins: 185 },
  } as Run;
  render(
    <RunDialog
      runs={[future, replay]}
      onClose={() => {}}
      onCreated={() => {}}
    />,
  );
  await screen.findByText("Base · v1");
  expect(screen.getByLabelText("Dự báo cha đã hoàn tất")).toHaveValue("replay");
});

it("labels pending lots at their frozen origin when viewing a later date", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(() => response(workspace));
  render(
    <Overview
      run={run()}
      ctx={{ ...ctx, origin: "2025-11-05" }}
      runs={[run()]}
      onRun={() => {}}
      onCreate={() => {}}
      onNavigate={() => {}}
      onItem={() => {}}
    />,
  );
  expect(
    await screen.findByText(/Các lô đã biết tại mốc 2025-10-31/),
  ).toBeVisible();
});

it("clears stale purchasing rows and export while a new search is pending", async () => {
  const fetch = vi
    .spyOn(globalThis, "fetch")
    .mockImplementation((url) =>
      String(url).includes("search=missing")
        ? new Promise(() => {})
        : response({
            items: [{ id: 1, sku: "TEST-SKU", item_id: 1 }],
            total: 120,
            summary: { recommended_items: 120 },
          }),
    );
  render(<Replenishment run={run()} ctx={ctx} />);
  await screen.findByText("TEST-SKU");
  fireEvent.click(screen.getByRole("button", { name: "Sau →" }));
  await waitFor(() =>
    expect(
      fetch.mock.calls.some(([url]) => String(url).includes("page=2")),
    ).toBe(true),
  );
  fireEvent.change(
    screen.getByRole("searchbox", { name: "Tìm trong danh sách nhập hàng" }),
    { target: { value: "missing" } },
  );
  expect(screen.queryByText("TEST-SKU")).toBeNull();
  expect(screen.queryByRole("link", { name: /Xuất CSV/ })).toBeNull();
  await waitFor(() =>
    expect(String(fetch.mock.calls.at(-1)?.[0])).toContain("search=missing"),
  );
  expect(String(fetch.mock.calls.at(-1)?.[0])).toContain("page=1");
});

it("opens an incoming lot and links its exact item to inventory", async () => {
  const row = {
    id: 7,
    item_id: 341,
    warehouse_id: 18,
    sku: "TEST-SKU",
    product_type: "eSIM",
    carrier: "Demo",
    destination_country: "DemoLand",
    ordered_on: "2025-10-28",
    eta: "2025-11-04",
    ordered_qty: 20,
    received_qty: 0,
    status: "ordered",
  };
  vi.spyOn(globalThis, "fetch").mockImplementation(() =>
    response({
      items: [row],
      total: 1,
      context: { known_orders_through: "2025-10-31" },
      summary: {
        incoming_lots: 1,
        pending_units: 20,
        inventory_available: true,
      },
    }),
  );
  const open = vi.fn();
  render(<Replenishment run={run()} ctx={ctx} view="incoming" onItem={open} />);
  fireEvent.click(await screen.findByText("Lô #7"));
  expect(screen.getByRole("dialog", { name: "Lô #7" })).toBeVisible();
  expect(
    screen.getByText("Đã nhận tại mốc dữ liệu").closest("div"),
  ).toHaveTextContent("0");
  fireEvent.click(screen.getByRole("button", { name: /Mở hồ sơ tồn kho/ }));
  expect(open).toHaveBeenCalledWith(row, "inventory");
});
