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
    { item_id: 341, configured_rop_floor: 43, moq: 11, safety_days: 1.25 },
  ]);
  expect(body?.settings.receipts_initial).toEqual([]);
  expect(body?.settings.receipts_declared).toBe(true);
});
