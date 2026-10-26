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
          ? [{ id: 1, code: "SUP-018", display_name: "Synthetic supplier" }]
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
  expect(screen.getByLabelText("Kho / tuyến")).toHaveValue("");
  expect(screen.getByLabelText("SKU")).toBeDisabled();
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
  render(<Configuration onChanged={changed} />);
  await screen.findByText("WH-018");
  fireEvent.click(screen.getByRole("button", { name: "Chính sách nhập hàng" }));
  fireEvent.click(
    screen.getByRole("button", { name: /Policy cho mặt hàng chưa cấu hình/ }),
  );
  const dialog = within(screen.getByRole("dialog"));
  fireEvent.change(dialog.getByLabelText("Kho để chọn mặt hàng"), {
    target: { value: "18" },
  });
  await dialog.findByRole("option", { name: "SYNTHETIC-SKU · eSIM" });
  fireEvent.change(dialog.getByLabelText("Mặt hàng"), {
    target: { value: "341" },
  });
  fireEvent.change(dialog.getByLabelText("Ngưỡng nhập tối thiểu (ROP floor)"), {
    target: { value: "42" },
  });
  fireEvent.change(dialog.getByLabelText("MOQ"), { target: { value: "9" } });
  fireEvent.change(dialog.getByLabelText("Số ngày tồn an toàn"), {
    target: { value: "1.5" },
  });
  const form = dialog
    .getByRole("button", { name: "Lưu phiên bản mới" })
    .closest("form")!;
  fireEvent.submit(form);
  await waitFor(() =>
    expect(dialog.getByRole("alert")).toHaveTextContent("Cấu hình đã thay đổi"),
  );
  expect(changed).not.toHaveBeenCalled();
  expect(dialog.getByLabelText("MOQ")).toHaveValue(9);
  fireEvent.submit(form);
  await waitFor(() => expect(changed).toHaveBeenCalledTimes(1));
  expect(bodies).toEqual(
    Array(2).fill({
      item_id: 341,
      supplier_id: 1,
      effective_from: "2026-01-01",
      configured_rop_floor: 42,
      moq: 9,
      safety_days: 1.5,
      safety_mode: "days",
      safety_lookback_days: 28,
      safety_factor: 1,
      rop_mode: "forecast",
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
  await screen.findByText("WH-018");
  fireEvent.click(screen.getByRole("button", { name: "Kịch bản" }));
  fireEvent.click(screen.getByRole("button", { name: "＋ Kịch bản mới" }));
  const dialog = within(screen.getByRole("dialog"));
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
  fireEvent.change(group.getByLabelText("Cách tính tồn an toàn (SS)"), {
    target: { value: "days" },
  });
  act(() => {
    fireEvent.change(
      group.getByLabelText("Ngưỡng nhập tối thiểu (ROP floor)"),
      { target: { value: "43" } },
    );
    fireEvent.change(group.getByLabelText("MOQ"), { target: { value: "11" } });
    fireEvent.change(group.getByLabelText("Số ngày tồn an toàn"), {
      target: { value: "1.25" },
    });
  });
  fireEvent.submit(
    dialog.getByRole("button", { name: "Lưu phiên bản mới" }).closest("form")!,
  );
  await waitFor(() => expect(body).toBeDefined());
  expect(body?.settings.policy_overrides).toEqual([
    { item_id: 341, configured_rop_floor: 43, moq: 11, safety_days: 1.25, safety_mode: "days" },
  ]);
  expect(body?.settings.receipts_initial).toEqual([]);
  expect(body?.settings.receipts_declared).toBe(true);
});

async function newPolicy() {
  render(<Configuration onChanged={() => {}} />);
  await screen.findByText("WH-018");
  fireEvent.click(screen.getByRole("button", { name: "Chính sách nhập hàng" }));
  fireEvent.click(screen.getByRole("button", { name: /Policy cho mặt hàng chưa cấu hình/ }));
  const dialog = within(screen.getByRole("dialog"));
  fireEvent.change(dialog.getByLabelText("Kho để chọn mặt hàng"), { target: { value: "18" } });
  await dialog.findByRole("option", { name: "SYNTHETIC-SKU · eSIM" });
  fireEvent.change(dialog.getByLabelText("Mặt hàng"), { target: { value: "341" } });
  return dialog;
}

it("saves volatility and fixed ROP while preserving inactive parameters across mode changes", async () => {
  let body: Record<string, any> | undefined;
  vi.spyOn(globalThis, "fetch").mockImplementation((input, options) => {
    if (options?.method !== "POST") return readReply(input);
    body = JSON.parse(String(options.body));
    return reply({ id: 1 });
  });
  const dialog = await newPolicy();
  fireEvent.change(dialog.getByLabelText("Số ngày tồn an toàn"), { target: { value: "3.5" } });
  fireEvent.change(dialog.getByLabelText("Cách tính tồn an toàn (SS)"), { target: { value: "volatility" } });
  expect(dialog.queryByLabelText("Số ngày tồn an toàn")).toBeNull();
  fireEvent.change(dialog.getByLabelText("Số ngày lịch sử quan sát"), { target: { value: "90" } });
  fireEvent.change(dialog.getByLabelText("Hệ số biến động"), { target: { value: "0" } });
  fireEvent.change(dialog.getByLabelText("Cách tính ngưỡng nhập (ROP)"), { target: { value: "fixed" } });
  expect(dialog.getByText(/không cộng tồn an toàn lần nữa/)).toBeVisible();
  fireEvent.change(dialog.getByLabelText("Số ngày nhìn trước cảnh báo xuống ROP"), { target: { value: "14" } });
  fireEvent.change(dialog.getByLabelText("Cách tính tồn an toàn (SS)"), { target: { value: "days" } });
  expect(dialog.getByLabelText("Số ngày tồn an toàn")).toHaveValue(3.5);
  expect(dialog.queryByLabelText("Hệ số biến động")).toBeNull();
  fireEvent.change(dialog.getByLabelText("Cách tính tồn an toàn (SS)"), { target: { value: "volatility" } });
  expect(dialog.getByLabelText("Hệ số biến động")).toHaveValue(0);
  fireEvent.submit(dialog.getByRole("button", { name: "Lưu phiên bản mới" }).closest("form")!);
  await waitFor(() => expect(body).toBeDefined());
  expect(body).toMatchObject({ safety_mode: "volatility", safety_days: 3.5, safety_lookback_days: 90,
    safety_factor: 0, rop_mode: "fixed", warning_horizon_days: 14, expected_version: 0 });
});

it("opens a historical policy with its exact modes and version and retains them after a conflict", async () => {
  const bodies: Record<string, any>[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation((input, options) => {
    if (options?.method === "POST") {
      bodies.push(JSON.parse(String(options.body)));
      return reply({ error: { code: "version_conflict", message: "synthetic" } }, false, 409);
    }
    if (String(input).includes("/supplier-item-policies")) return reply({ items: [{
      id: 11, item_id: 341, item_label: "Historical SKU", supplier_id: 1, supplier_code: "SUP-018", version: 4,
      effective_from: "2025-11-01", effective_to: "2026-01-01", configured_rop_floor: 20, moq: 9,
      safety_mode: "volatility", safety_days: 2, safety_lookback_days: 7, safety_factor: 2.5,
      rop_mode: "fixed", warning_horizon_days: 1,
    }], total: 1, page: 1, page_size: 50 });
    return readReply(input);
  });
  render(<Configuration onChanged={() => {}} />);
  await screen.findByText("WH-018");
  fireEvent.click(screen.getByRole("button", { name: "Chính sách nhập hàng" }));
  fireEvent.click(await screen.findByText("Historical SKU"));
  const dialog = within(screen.getByRole("dialog"));
  expect(dialog.getByLabelText("Cách tính tồn an toàn (SS)")).toHaveValue("volatility");
  expect(dialog.getByLabelText("Số ngày lịch sử quan sát")).toHaveValue(7);
  expect(dialog.getByLabelText("Hệ số biến động")).toHaveValue(2.5);
  expect(dialog.getByLabelText("Cách tính ngưỡng nhập (ROP)")).toHaveValue("fixed");
  expect(dialog.getByLabelText("Số ngày nhìn trước cảnh báo xuống ROP")).toHaveValue(1);
  fireEvent.change(dialog.getByLabelText("Hiệu lực từ"), { target: { value: "2026-02-01" } });
  const form = dialog.getByRole("button", { name: "Lưu phiên bản mới" }).closest("form")!;
  fireEvent.submit(form);
  await waitFor(() => expect(dialog.getByRole("alert")).toBeVisible());
  expect(dialog.getByLabelText("Hệ số biến động")).toHaveValue(2.5);
  fireEvent.submit(form);
  await waitFor(() => expect(bodies).toHaveLength(2));
  expect(bodies[0]).toEqual(bodies[1]);
  expect(bodies[0]).toMatchObject({ expected_version: 4, effective_from: "2026-02-01", safety_mode: "volatility", safety_lookback_days: 7, safety_factor: 2.5, rop_mode: "fixed", warning_horizon_days: 1 });
});

it.each([
  ["Số ngày nhìn trước cảnh báo xuống ROP", "0"],
  ["Số ngày nhìn trước cảnh báo xuống ROP", "15"],
  ["Số ngày nhìn trước cảnh báo xuống ROP", "1.5"],
  ["Số ngày lịch sử quan sát", "6"],
  ["Số ngày lịch sử quan sát", "91"],
  ["Hệ số biến động", "-1"],
])("blocks an invalid native field before POST: %s=%s", async (label, value) => {
  const post = vi.fn();
  vi.spyOn(globalThis, "fetch").mockImplementation((input, options) => {
    if (options?.method === "POST") { post(); return reply({ id: 1 }); }
    return readReply(input);
  });
  const dialog = await newPolicy();
  fireEvent.change(dialog.getByLabelText("Cách tính tồn an toàn (SS)"), { target: { value: "volatility" } });
  fireEvent.change(dialog.getByLabelText(label), { target: { value } });
  const form = dialog.getByRole("button", { name: "Lưu phiên bản mới" }).closest("form")!;
  expect(form.checkValidity()).toBe(false);
  fireEvent.submit(form);
  expect(post).not.toHaveBeenCalled();
});

it("keeps blank override fields inherited, preserves zero and omits inactive mode parameters", async () => {
  let body: Record<string, any> | undefined;
  vi.spyOn(globalThis, "fetch").mockImplementation((input, options) => {
    if (options?.method !== "POST") return readReply(input);
    body = JSON.parse(String(options.body)); return reply({ id: 1 });
  });
  render(<Configuration onChanged={() => {}} />);
  await screen.findByText("WH-018");
  fireEvent.click(screen.getByRole("button", { name: "Kịch bản" }));
  fireEvent.click(screen.getByRole("button", { name: "＋ Kịch bản mới" }));
  const dialog = within(screen.getByRole("dialog"));
  fireEvent.change(dialog.getByLabelText("Tên kịch bản"), { target: { value: "Inherited" } });
  fireEvent.change(dialog.getByLabelText("Mã kịch bản"), { target: { value: "inherited" } });
  fireEvent.change(dialog.getByLabelText("Kho để chọn mặt hàng"), { target: { value: "18" } });
  const add = dialog.getByRole("button", { name: "＋ Điều chỉnh mặt hàng" });
  await waitFor(() => expect(add).toBeEnabled()); fireEvent.click(add);
  const group = within(dialog.getByRole("group", { name: "Điều chỉnh riêng mặt hàng" }));
  expect(group.getByLabelText("Cách tính tồn an toàn (SS)")).toHaveValue("");
  fireEvent.change(group.getByLabelText("Ngưỡng nhập tối thiểu (ROP floor)"), { target: { value: "12" } });
  fireEvent.change(group.getByLabelText("Ngưỡng nhập tối thiểu (ROP floor)"), { target: { value: "" } });
  fireEvent.change(group.getByLabelText("Cách tính tồn an toàn (SS)"), { target: { value: "days" } });
  fireEvent.change(group.getByLabelText("Số ngày tồn an toàn"), { target: { value: "3" } });
  fireEvent.change(group.getByLabelText("Cách tính tồn an toàn (SS)"), { target: { value: "volatility" } });
  fireEvent.change(group.getByLabelText("Hệ số biến động"), { target: { value: "0" } });
  fireEvent.change(group.getByLabelText("Số ngày nhìn trước cảnh báo xuống ROP"), { target: { value: "1" } });
  fireEvent.submit(dialog.getByRole("button", { name: "Lưu phiên bản mới" }).closest("form")!);
  await waitFor(() => expect(body).toBeDefined());
  expect(body?.settings.policy_overrides).toEqual([{ item_id: 341, safety_mode: "volatility", safety_factor: 0, warning_horizon_days: 1 }]);
});
