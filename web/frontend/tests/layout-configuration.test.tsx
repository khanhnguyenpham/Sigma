import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import App from "../src/App";
import { Configuration } from "../src/pages/Configuration";
import { ProductPolicyForm } from "../src/components/products/ProductPolicyForm";
import type { Run } from "../src/types/api";

const reply = (body: unknown, ok = true, status = 200) =>
  Promise.resolve({ ok, status, json: async () => body } as Response);
const runs: Run[] = ["plan-a", "plan-b"].map((id, index) => ({
  id,
  kind: "stock_projection",
  status: "complete",
  as_of_date: index ? "2025-11-02" : "2025-10-31",
  observation_end: "2025-12-31",
  result_summary: { inventory_available: true },
  config_version: "synthetic",
  assumption_version: "synthetic",
  target_version: "synthetic",
  source_import_run_id: "source",
  forecast_run_id: "forecast",
  scenario_id: 1,
  error_code: null,
  period_start: null,
  period_end: null,
  created_at: "2026-10-25T00:00:00Z",
}));
function readReply(input: RequestInfo | URL) {
  const url = String(input);
  const items = url.includes("/runs?")
    ? runs
    : url.includes("/warehouses")
      ? [
          {
            id: 18,
            code: "WH-018",
            destination_country: "Demo",
            carrier: "DemoNet",
            city: "Synthetic",
            version: 1,
          },
        ]
      : url.includes("/items")
        ? [{ id: 341, sku: "SYNTHETIC-SKU", product_type: "eSIM" }]
        : url.includes("/suppliers")
          ? [{ id: 1, carrier: "DemoNet" }]
          : [];
  return reply({
    items,
    total: items.length,
    page: 1,
    page_size: 50,
    summary: {},
    attention: [],
    incoming: [],
    route_stock: [],
  });
}
beforeEach(() => {
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
});

it("uses the selected product supplier without offering unrelated carriers", async () => {
  const bodies: Record<string, unknown>[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation((_input, options) => {
    bodies.push(JSON.parse(String(options?.body))); return reply({ id: 1 });
  });
  render(<ProductPolicyForm product={{ id: 341, supplier_id: 1, policy: null }} onSaved={() => {}} onReload={() => {}} />);
  expect(screen.queryByLabelText("Nhà cung cấp")).toBeNull();
  fireEvent.change(screen.getByLabelText("Lượng nhập mỗi lần"), { target: { value: "12" } });
  fireEvent.submit(screen.getByRole("form", { name: "Cấu hình nhập hàng sản phẩm" }));
  await waitFor(() => expect(bodies).toHaveLength(1));
  expect(bodies[0]).toMatchObject({ item_id: 341, supplier_id: 1, expected_version: 0 });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  history.replaceState(null, "", "/");
});

it("restores run/date/purchasing view through Back and reload and clears incompatible filters", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(readReply);
  history.replaceState(
    null,
    "",
    "/?run_id=plan-a&warehouse_id=18&item_id=341&origin=2025-10-31#inventory",
  );
  const first = render(<App />);
  await waitFor(() =>
    expect(screen.getByLabelText("Lượt chạy")).toHaveValue("plan-a"),
  );
  fireEvent.change(screen.getByLabelText("Lượt chạy"), {
    target: { value: "plan-b" },
  });
  await waitFor(() =>
    expect(screen.getByLabelText("Ngày xem / origin UTC")).toHaveValue(
      "2025-11-02",
    ),
  );
  expect(screen.queryByLabelText("Kho / tuyến")).toBeNull();
  expect(screen.queryByLabelText("SKU")).toBeNull();
  await screen.findByRole("heading", { name: "Danh sách kho" });
  expect(location.search).not.toContain("warehouse_id");
  await waitFor(() => expect(location.search).not.toContain("item_id"));
  fireEvent.click(
    screen.getByRole("button", { name: "Nhập hàng" }),
  );
  fireEvent.click(await screen.findByRole("button", { name: /^Đang về/ }));
  await waitFor(() => expect(location.search).toContain("view=incoming"));
  fireEvent.click(
    screen.getByRole("button", { name: "Cảnh báo" }),
  );
  await waitFor(() => expect(location.hash).toBe("#alerts"));
  act(() => history.back());
  await waitFor(() => expect(location.hash).toBe("#replenishment"));
  expect(await screen.findByRole("button", { name: /^Đang về/ })).toHaveClass(
    "active",
  );
  first.unmount();
  render(<App />);
  await waitFor(() =>
    expect(screen.getByLabelText("Lượt chạy")).toHaveValue("plan-b"),
  );
  expect(screen.getByLabelText("Ngày xem / origin UTC")).toHaveValue(
    "2025-11-02",
  );
  expect(await screen.findByRole("button", { name: /^Đang về/ })).toHaveClass(
    "active",
  );
});

it("closes the navigation with Escape and returns focus to its menu trigger", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(readReply);
  render(<App />);
  const trigger = screen.getByRole("button", { name: "Mở menu" });
  fireEvent.click(trigger);
  expect(trigger).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByRole("button", { name: "Đóng menu" })).toBeInTheDocument();
  fireEvent.keyDown(window, { key: "Escape" });
  expect(trigger).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByRole("button", { name: "Đóng menu" })).toBeNull();
  expect(trigger).toHaveFocus();
});

it("retains policy values after 409 and saves the same native fields on explicit retry", async () => {
  const bodies: unknown[] = [],
    changed = vi.fn();
  vi.spyOn(globalThis, "fetch").mockImplementation((input, options) => {
    if (options?.method !== "POST") return readReply(input);
    bodies.push(JSON.parse(String(options.body)));
    return bodies.length === 1
      ? reply(
          {
            error: { code: "version_conflict", message: "synthetic conflict" },
          },
          false,
          409,
        )
      : reply({ id: 1 });
  });
  render(<ProductPolicyForm product={{ id: 341, supplier_id: 1, policy: null }} onSaved={changed} onReload={() => {}} />);
  const dialog = within(screen.getByRole("form", { name: "Cấu hình nhập hàng sản phẩm" }));
  fireEvent.change(dialog.getByLabelText("Ngưỡng nhập cố định (ROP)"), {
    target: { value: "42" },
  });
  fireEvent.change(dialog.getByLabelText("Lượng nhập mỗi lần"), { target: { value: "9" } });
  fireEvent.change(dialog.getByLabelText("Số ngày tồn an toàn"), {
    target: { value: "1.5" },
  });
  const form = dialog
    .getByRole("button", { name: "Lưu cấu hình sản phẩm" })
    .closest("form")!;
  fireEvent.submit(form);
  await waitFor(() =>
    expect(dialog.getByRole("alert")).toHaveTextContent("Cấu hình đã thay đổi"),
  );
  expect(changed).not.toHaveBeenCalled();
  expect(dialog.getByLabelText("Lượng nhập mỗi lần")).toHaveValue(9);
  fireEvent.submit(form);
  await waitFor(() => expect(changed).toHaveBeenCalledTimes(1));
  expect(bodies).toEqual(
    Array(2).fill({
      item_id: 341,
      supplier_id: 1,
      effective_from: new Date().toISOString().slice(0, 10),
      configured_rop_floor: 42,
      fixed_order_qty: 9,
      safety_days: 1.5,
      warning_horizon_days: 7,
      expected_version: 0,
    }),
  );
});

it("keeps batched override field edits in the scenario payload", async () => {
  let body: Record<string, any> | undefined;
  vi.spyOn(globalThis, "fetch").mockImplementation((input, options) => {
    if (options?.method !== "POST") return readReply(input);
    body = JSON.parse(String(options.body));
    return reply({ id: 1 });
  });
  render(<Configuration onChanged={() => {}} />);
  fireEvent.click(screen.getByRole("button", { name: "＋ Kịch bản mới" }));
  const dialog = within(screen.getByRole("dialog"));
  await dialog.findByRole("option", { name: "Synthetic" });
  fireEvent.change(dialog.getByLabelText("Tên kịch bản"), {
    target: { value: "Synthetic override" },
  });
  fireEvent.change(dialog.getByLabelText("Mã kịch bản"), {
    target: { value: "synthetic_override" },
  });
  fireEvent.change(dialog.getByLabelText("Kho để chọn mặt hàng"), {
    target: { value: "18" },
  });
  await waitFor(() =>
    expect(
      dialog.getByRole("button", { name: "＋ Điều chỉnh mặt hàng" }),
    ).toBeEnabled(),
  );
  fireEvent.click(
    dialog.getByRole("button", { name: "＋ Điều chỉnh mặt hàng" }),
  );
  const group = within(
    dialog.getByRole("group", { name: "Điều chỉnh riêng mặt hàng" }),
  );
  act(() => {
    fireEvent.change(
      group.getByLabelText("Ngưỡng nhập cố định (ROP)"),
      { target: { value: "43" } },
    );
    expect(group.queryByLabelText("Lượng nhập mỗi lần")).toBeNull();
    expect(group.queryByLabelText("MOQ")).toBeNull();
    fireEvent.change(group.getByLabelText("Số ngày tồn an toàn"), {
      target: { value: "1.25" },
    });
  });
  fireEvent.submit(
    dialog.getByRole("button", { name: "Lưu phiên bản mới" }).closest("form")!,
  );
  await waitFor(() => expect(body).toBeDefined());
  expect(body?.settings.policy_overrides).toEqual([
    { item_id: 341, configured_rop_floor: 43, safety_days: 1.25 },
  ]);
  expect(body?.settings.receipts_initial).toEqual([]);
  expect(body?.settings.receipts_declared).toBe(true);
});

async function newPolicy() {
  render(<ProductPolicyForm product={{ id: 341, supplier_id: 1, policy: null }} onSaved={() => {}} onReload={() => {}} />);
  const dialog = within(screen.getByRole("form", { name: "Cấu hình nhập hàng sản phẩm" }));
  fireEvent.change(dialog.getByLabelText("Lượng nhập mỗi lần"), { target: { value: "17" } });
  return dialog;
}

it("uses fixed ROP and days SS without selectors or retired request fields", async () => {
  let body: Record<string, unknown> | undefined;
  vi.spyOn(globalThis, "fetch").mockImplementation((_input, options) => { body=JSON.parse(String(options?.body)); return reply({id:1}); });
  const form=await newPolicy();
  expect(form.queryByLabelText("Cách tính tồn an toàn (SS)")).toBeNull();
  expect(form.queryByLabelText("Cách tính ngưỡng nhập (ROP)")).toBeNull();
  expect(form.queryByLabelText("Hệ số biến động")).toBeNull();
  fireEvent.change(form.getByLabelText("Số ngày tồn an toàn"),{target:{value:"0"}});
  fireEvent.change(form.getByLabelText("Ngưỡng nhập cố định (ROP)"),{target:{value:"0"}});
  fireEvent.submit(form.getByRole("button",{name:"Lưu cấu hình sản phẩm"}).closest('form')!);
  await waitFor(()=>expect(body).toBeDefined());
  expect(body).toMatchObject({configured_rop_floor:0,safety_days:0,fixed_order_qty:17});
  for(const key of ['safety_mode','rop_mode','safety_lookback_days','safety_factor']) expect(body).not.toHaveProperty(key);
});

it("retains saved SS days and entered quantity after a version conflict", async () => {
  const bodies: Record<string, any>[]=[];
  vi.spyOn(globalThis,"fetch").mockImplementation((_input,options)=>{
    bodies.push(JSON.parse(String(options?.body)));
    return reply({error:{code:'version_conflict',message:'synthetic'}},false,409);
  });
  render(<ProductPolicyForm product={{id:341,supplier_id:1,policy:{version:4,effective_from:'2025-11-01',configured_rop_floor:20,safety_days:2,warning_horizon_days:1}}} onSaved={()=>{}} onReload={()=>{}} />);
  const form=within(screen.getByRole('form',{name:'Cấu hình nhập hàng sản phẩm'}));
  expect(form.getByLabelText('Số ngày tồn an toàn')).toHaveValue(2);
  fireEvent.change(form.getByLabelText('Lượng nhập mỗi lần'),{target:{value:'30'}});
  fireEvent.change(form.getByLabelText('Số ngày tồn an toàn'),{target:{value:'3.5'}});
  const node=form.getByRole('button',{name:'Lưu cấu hình sản phẩm'}).closest('form')!;
  fireEvent.submit(node); await form.findByRole('alert');
  expect(form.getByLabelText('Số ngày tồn an toàn')).toHaveValue(3.5);
  fireEvent.submit(node); await waitFor(()=>expect(bodies).toHaveLength(2));
  expect(bodies[0]).toEqual(bodies[1]);
  expect(bodies[0]).toMatchObject({expected_version:4,fixed_order_qty:30,safety_days:3.5,configured_rop_floor:20,warning_horizon_days:1});
});

it.each([
  ["Lượng nhập mỗi lần", ""],
  ["Lượng nhập mỗi lần", "0"],
  ["Lượng nhập mỗi lần", "1.5"],
  ["Số ngày nhìn trước cảnh báo xuống ROP", "0"],
  ["Số ngày nhìn trước cảnh báo xuống ROP", "15"],
  ["Số ngày nhìn trước cảnh báo xuống ROP", "1.5"],
  ["Số ngày tồn an toàn", "-1"],
  ["Ngưỡng nhập cố định (ROP)", "-1"],
  ["Ngưỡng nhập cố định (ROP)", "1.5"],
])("blocks an invalid native field before POST: %s=%s", async (label, value) => {
  const post = vi.fn();
  vi.spyOn(globalThis, "fetch").mockImplementation((input, options) => {
    if (options?.method === "POST") { post(); return reply({ id: 1 }); }
    return readReply(input);
  });
  const dialog = await newPolicy();
  fireEvent.change(dialog.getByLabelText(label), { target: { value } });
  const form = dialog.getByRole("button", { name: "Lưu cấu hình sản phẩm" }).closest("form")!;
  expect(form.checkValidity()).toBe(false);
  fireEvent.submit(form);
  expect(post).not.toHaveBeenCalled();
});

it("keeps blank numeric overrides inherited and preserves zero SS days", async () => {
  let body: Record<string, any> | undefined;
  vi.spyOn(globalThis, "fetch").mockImplementation((input, options) => {
    if (options?.method !== "POST") return readReply(input);
    body = JSON.parse(String(options.body)); return reply({ id: 1 });
  });
  render(<Configuration onChanged={() => {}} />);
  fireEvent.click(screen.getByRole("button", { name: "＋ Kịch bản mới" }));
  const dialog = within(screen.getByRole("dialog"));
  await dialog.findByRole("option", { name: "Synthetic" });
  fireEvent.change(dialog.getByLabelText("Tên kịch bản"), { target: { value: "Inherited" } });
  fireEvent.change(dialog.getByLabelText("Mã kịch bản"), { target: { value: "inherited" } });
  fireEvent.change(dialog.getByLabelText("Kho để chọn mặt hàng"), { target: { value: "18" } });
  const add = dialog.getByRole("button", { name: "＋ Điều chỉnh mặt hàng" });
  await waitFor(() => expect(add).toBeEnabled()); fireEvent.click(add);
  const group = within(dialog.getByRole("group", { name: "Điều chỉnh riêng mặt hàng" }));
  expect(group.queryByLabelText("Cách tính tồn an toàn (SS)")).toBeNull();
  fireEvent.change(group.getByLabelText("Ngưỡng nhập cố định (ROP)"), { target: { value: "12" } });
  fireEvent.change(group.getByLabelText("Ngưỡng nhập cố định (ROP)"), { target: { value: "" } });
  fireEvent.change(group.getByLabelText("Số ngày tồn an toàn"), { target: { value: "0" } });
  fireEvent.change(group.getByLabelText("Số ngày nhìn trước cảnh báo xuống ROP"), { target: { value: "1" } });
  fireEvent.submit(dialog.getByRole("button", { name: "Lưu phiên bản mới" }).closest("form")!);
  await waitFor(() => expect(body).toBeDefined());
  expect(body?.settings.policy_overrides).toEqual([{ item_id: 341, safety_days: 0, warning_horizon_days: 1 }]);
});
