import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Configuration } from "../src/pages/Configuration";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
it("preserves receipt date and quantity when inputs change in the same batch", async () => {
  let posted: Record<string, any> | undefined;
  vi.spyOn(globalThis, "fetch").mockImplementation((input, options) => {
    if (options?.method === "POST") {
      posted = JSON.parse(String(options.body));
      return Promise.resolve({
        ok: true,
        json: async () => ({ id: 1 }),
      } as Response);
    }
    const url = String(input);
    const items = url.includes("/warehouses")
      ? [
          {
            id: 18,
            code: "WH-018",
            destination_country: "Japan",
            carrier: "NTT Docomo",
            city: "Tokyo",
            version: 1,
          },
        ]
      : url.includes("/items")
        ? [{ id: 341, sku: "DEMO-SKU", product_type: "eSIM" }]
        : [];
    return Promise.resolve({
      ok: true,
      json: async () => ({
        items,
        total: items.length,
        page: 1,
        page_size: 50,
      }),
    } as Response);
  });
  render(<Configuration onChanged={() => {}} />);
  await screen.findByText("WH-018");
  fireEvent.click(
    screen.getByRole("button", { name: "Kịch bản" }),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "＋ Kịch bản mới" }),
  );
  const dialog = within(screen.getByRole("dialog"));
  fireEvent.change(
    dialog.getByRole("textbox", { name: "Tên kịch bản" }),
    { target: { value: "Receipt fixture" } },
  );
  fireEvent.change(
    dialog.getByRole("textbox", { name: "Mã kịch bản" }),
    { target: { value: "receipt_fixture" } },
  );
  fireEvent.change(
    dialog.getByRole("combobox", { name: "Kho để chọn mặt hàng" }),
    { target: { value: "18" } },
  );
  await waitFor(() =>
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/v1/items?warehouse_id=18&page_size=100",
      expect.anything(),
    ),
  );
  await act(async () => {});
  fireEvent.click(
    dialog.getByRole("button", { name: "＋ Lô đang về" }),
  );
  const date = dialog.getByLabelText("Ngày đặt", { }),
    quantity = dialog.getByRole("spinbutton", {
      name: "Số lượng",
    });
  act(() => {
    fireEvent.change(date, { target: { value: "2025-10-28" } });
    fireEvent.change(quantity, { target: { value: "20" } });
  });
  fireEvent.submit(
    dialog.getByRole("button", { name: "Lưu phiên bản mới" }).closest("form")!,
  );
  await waitFor(() => expect(posted).toBeDefined());
  expect(posted?.settings.receipts_initial[0]).toMatchObject({
    item_id: 341,
    ordered_on: "2025-10-28",
    eta: "2025-11-04",
    ordered_qty: 20,
  });
});
