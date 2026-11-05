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
import { ScenarioEditor } from "../src/components/configuration/ScenarioEditor";
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
    const items = url.includes("/suppliers")
      ? [{id:1,carrier:'NTT Docomo'}]
      : url.includes("/products")
        ? [{ id: 341, sku: "DEMO-SKU", product_type: "eSIM",carrier:'NTT Docomo',city:'Tokyo',destination_country:'Japan' }]
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
  render(<ScenarioEditor onSaved={() => {}} onRefresh={() => {}} onDirty={() => {}} onBusy={() => {}} />);
  const dialog = within(screen.getByRole("form", { name: "Thiết lập kịch bản" }));
  fireEvent.change(
    dialog.getByRole("textbox", { name: "Tên kịch bản" }),
    { target: { value: "Receipt fixture" } },
  );
  fireEvent.change(
    dialog.getByRole("textbox", { name: "Mã kịch bản" }),
    { target: { value: "receipt_fixture" } },
  );
  fireEvent.click(
    dialog.getByRole("button", { name: "＋ Lô đang về" }),
  );
  const picker=within(screen.getByRole('dialog',{name:'Chọn mặt hàng cho lô đang về'}));
  await picker.findByRole('option',{name:'NTT Docomo'});
  fireEvent.change(picker.getByLabelText('Nhà mạng'),{target:{value:'NTT Docomo'}});
  fireEvent.click(await picker.findByRole('button',{name:'Chọn DEMO-SKU eSIM tại Tokyo'}));
  const date = dialog.getByLabelText("Ngày đặt", { }),
    quantity = dialog.getByRole("spinbutton", {
      name: "Số lượng",
    });
  act(() => {
    fireEvent.change(date, { target: { value: "2025-10-28" } });
    fireEvent.change(quantity, { target: { value: "20" } });
  });
  fireEvent.submit(
    dialog.getByRole("button", { name: "Lưu thiết lập" }).closest("form")!,
  );
  await waitFor(() => expect(posted).toBeDefined());
  expect(posted?.settings.receipts_initial[0]).toMatchObject({
    item_id: 341,
    ordered_on: "2025-10-28",
    eta: "2025-11-04",
    ordered_qty: 20,
  });
});
