import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import App from "../src/App";
import { Products, ProductDetail } from "../src/pages/Products";
import { WarehouseEditor } from "../src/components/inventory/WarehouseEditor";
import type { Context } from "../src/types/context";

const warehouse = { id: 1, city: "Melbourne", code: "WH-SYN", destination_country: "Australia", carrier: "Telstra", version: 2 };
const product = { id: 11, item_id: 11, warehouse_id: 1, sku: "SYNTHETIC-SKU", product_type: "eSIM", city: "Melbourne",
  destination_country: "Australia", carrier: "Telstra", supplier_id: 7, warehouse, policy: null, first_seen_date: "2024-01-01",
  supply_schema_ready:true,trade_schema_ready:true,internal_status:"active",provider_status:"clear",internal_version:0,supply_version:0 };
const run = { id: "plan", kind: "stock_projection", status: "complete", as_of_date: "2025-10-31", result_summary: { inventory_available: true } };
const stock = { ...product, closing_qty: 7, rop: 10, recommended_qty: 20, needs_replenishment: true };
const reply = (value: unknown, status = 200) => Promise.resolve({ ok: status === 200, status, json: async () => value } as Response);
const ctx: Context = { runId: "plan", origin: "2025-10-31", warehouseId: "1", itemId: "11", supplierId: "", productType: "" };
let latest: Record<string, unknown> | null;
const writes: Record<string, unknown>[] = [];
const reads: string[] = [];
function read(input: RequestInfo | URL, options?: RequestInit) {
  const url = new URL(String(input), "http://localhost"); reads.push(url.pathname + url.search);
  if (options?.method === "POST") { const body = JSON.parse(String(options.body)); writes.push(body); latest = { ...body, version: 1 }; return reply(latest); }
  if (url.pathname.endsWith('/runs')) return reply({ items: [run], total: 1 });
  if (url.pathname.endsWith('/warehouses')) return reply({ items: [warehouse], total: 1 });
  if (url.pathname.endsWith('/warehouses/1')) return reply(warehouse);
  if (url.pathname.endsWith('/products/11')) return reply({ ...product, policy: latest });
  if (url.pathname.endsWith('/products')) return reply({ items: [product], total: 51 });
  if (url.pathname.endsWith('/items')) return reply({ items: [], total: 0 });
  if (url.pathname.endsWith('/suppliers')) return reply({ items: [{ id: 7, carrier: "Telstra" }], total: 1 });
  if (url.pathname.endsWith('/workspace')) return reply({ summary: { item_count: 1 }, warehouse_stock: [], attention: [], incoming: [] });
  return reply({ items: [stock], total: 1 });
}
beforeEach(() => {
  latest = null; writes.length = 0; reads.length = 0;
  history.replaceState(null, '', '/');
  vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
  vi.spyOn(globalThis, 'fetch').mockImplementation(read);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); history.replaceState(null, '', '/'); });

it('lists current products without a run and filters on the server before pagination', async () => {
  const open = vi.fn(); render(<Products onOpen={open} />);
  await screen.findByText('SYNTHETIC-SKU');
  await waitFor(()=>expect(screen.getByLabelText('Trạng thái nhập')).toBeEnabled());
  fireEvent.click(await screen.findByRole('button',{name:'SYNTHETIC-SKU'}));
  expect(open).toHaveBeenCalledWith(expect.objectContaining({ id: 11, supplier_id: 7 }));
  fireEvent.click(screen.getByRole('button', { name: 'Sau →' }));
  await waitFor(() => expect(reads.at(-1)).toContain('page=2'));
  fireEvent.change(screen.getByLabelText('Tìm sản phẩm'), { target: { value: 'SKU' } });
  fireEvent.change(screen.getByLabelText('Kho sản phẩm'), { target: { value: '1' } });
  fireEvent.change(screen.getByLabelText('Loại sản phẩm'), { target: { value: 'eSIM' } });
  await waitFor(() => expect(reads.at(-1)).toContain('search=SKU&warehouse_id=1&product_type=eSIM&page=1'));
  expect(screen.queryByLabelText('Lượt chạy')).toBeNull();
});

it('filters by carrier before pagination and exposes distinct row actions without a date filter', async () => {
  const open=vi.fn(),supply=vi.fn();render(<Products onOpen={open} onSupply={supply} ctx={ctx}/>);
  await screen.findByText('SYNTHETIC-SKU');
  expect(screen.queryByLabelText('Ngày xem trạng thái (UTC)')).toBeNull();
  await waitFor(()=>expect(screen.getByLabelText('Trạng thái nhập')).toBeEnabled());
  fireEvent.change(screen.getByLabelText('Nhà mạng'),{target:{value:'Telstra'}});
  await waitFor(()=>expect(reads.at(-1)).toContain('carrier=Telstra'));
  expect(reads.at(-1)).toContain('page=1');
  fireEvent.click(await screen.findByRole('button',{name:/^Lịch cung cấp SYNTHETIC-SKU/}));
  expect(supply).toHaveBeenCalledWith(expect.objectContaining({id:11,warehouse_id:1}));expect(open).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:/^Cấu hình SYNTHETIC-SKU/}));expect(open).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByRole('button',{name:'Xóa bộ lọc'}));
  await waitFor(()=>expect(reads.at(-1)).not.toContain('carrier='));
});

it('opens the product-specific supply page and keeps its product on reload',async()=>{
  history.replaceState(null,'','/?run_id=plan&origin=2025-10-31#products');
  let view=render(<App/>);await screen.findByRole('button',{name:/^Lịch cung cấp SYNTHETIC-SKU/});
  await waitFor(()=>expect(screen.getByLabelText('Trạng thái nhập')).toBeEnabled());
  fireEvent.click(await screen.findByRole('button',{name:/^Lịch cung cấp SYNTHETIC-SKU/}));
  await screen.findByRole('heading',{name:'Lịch cung cấp',level:1});
  expect(location.hash).toBe('#product-supply');expect(location.search).toContain('item_id=11');
  await waitFor(()=>expect(reads.some(url=>url.includes('/provider-product-notices?')&&url.includes('item_id=11'))).toBe(true));
  expect(screen.queryByRole('button',{name:'Thông báo ngừng sản phẩm'})).toBeNull();
  view.unmount();view=render(<App/>);
  expect(await screen.findByRole('heading',{name:'Lịch cung cấp',level:1})).toBeVisible();
  expect(location.search).toContain('item_id=11');
});

it('opens a product page from inventory, saves its configuration and returns to the warehouse', async () => {
  history.replaceState(null, '', '/?run_id=plan&warehouse_id=1&origin=2025-10-31#inventory');
  render(<App />);
  fireEvent.click(await screen.findByText('SYNTHETIC-SKU'));
  await screen.findByRole('heading', { name: 'SYNTHETIC-SKU', level: 1 });
  expect(location.hash).toBe('#product'); expect(location.search).toContain('item_id=11');
  expect(screen.queryByRole('dialog')).toBeNull();
  const form = screen.getByRole('form', { name: 'Cấu hình nhập hàng sản phẩm' });
  fireEvent.change(within(form).getByLabelText('Lượng nhập mỗi lần'), { target: { value: '25' } });
  fireEvent.change(within(form).getByLabelText('Số ngày tồn an toàn'), { target: { value: '3' } });
  fireEvent.submit(form);
  await screen.findByText('Đã lưu cấu hình sản phẩm.');
  await waitFor(() => expect(screen.getByLabelText('Lượng nhập mỗi lần')).toHaveValue(25));
  expect(writes[0]).toMatchObject({ item_id: 11, supplier_id: 7, fixed_order_qty: 25, safety_days: 3, expected_version: 0 });
  fireEvent.click(screen.getByRole('button', { name: 'Xem sản phẩm trong kho' }));
  await screen.findByRole('heading', { name: 'Melbourne', level: 1 });
  expect(location.hash).toBe('#inventory'); expect(location.search).not.toContain('item_id');
  act(() => history.back());
  await waitFor(() => expect(location.hash).toBe('#product'));
  expect(await screen.findByRole('heading', { name: 'SYNTHETIC-SKU', level: 1 })).toBeVisible();
});

it('supports a product deep link and reload even when the item option page does not contain it', async () => {
  history.replaceState(null, '', '/?run_id=plan&warehouse_id=1&item_id=11&origin=2025-10-31#product');
  let view = render(<App />);
  await screen.findByRole('heading', { name: 'SYNTHETIC-SKU', level: 1 });
  expect(location.search).toContain('item_id=11');
  view.unmount(); view = render(<App />);
  expect(await screen.findByRole('heading', { name: 'SYNTHETIC-SKU', level: 1 })).toBeVisible();
  expect(screen.queryByLabelText('Lượt chạy')).toBeNull();
  expect(screen.queryByText(/phương án cũ/i)).toBeNull();
  view.unmount();
});

it('does not show a previous product while a different detail response is pending', async () => {
  let finish: ((value: Response) => void) | undefined;
  vi.mocked(fetch).mockImplementation((input, options) => String(input).includes('/products/22')
    ? new Promise((resolve) => { finish = resolve; }) : read(input, options));
  const view = render(<ProductDetail ctx={ctx} onNavigate={() => {}} onWarehouse={() => {}} onItem={() => {}} />);
  await screen.findByRole('heading', { name: 'SYNTHETIC-SKU', level: 1 });
  view.rerender(<ProductDetail ctx={{ ...ctx, itemId: '22' }} onNavigate={() => {}} onWarehouse={() => {}} onItem={() => {}} />);
  expect(screen.queryByRole('heading', { name: 'SYNTHETIC-SKU', level: 1 })).toBeNull();
  await act(async () => finish!({ ok: true, json: async () => ({ ...product, id: 22, sku: 'NEXT-SKU' }) } as Response));
  expect(await screen.findByRole('heading', { name: 'NEXT-SKU', level: 1 })).toBeVisible();
});

it('edits a warehouse in place with a version check and retains input after conflict', async () => {
  const close = vi.fn(); const bodies: unknown[] = [];
  vi.mocked(fetch).mockImplementation((input, options) => {
    if (options?.method !== 'PATCH') return read(input, options);
    bodies.push(JSON.parse(String(options.body)));
    return bodies.length === 1 ? reply({ error: { code: 'version_conflict', message: 'Changed' } }, 409) : reply({ ...warehouse, city: 'New City', version: 3 });
  });
  render(<WarehouseEditor id="1" onClose={close} />);
  const name = await screen.findByLabelText('Tên kho');
  fireEvent.change(name, { target: { value: 'New City' } });
  const form = screen.getByRole('button', { name: 'Lưu thông tin kho' }).closest('form')!;
  fireEvent.submit(form);
  await screen.findByRole('alert'); expect(name).toHaveValue('New City'); expect(close).not.toHaveBeenCalled();
  fireEvent.submit(form); await waitFor(() => expect(close).toHaveBeenCalledTimes(1));
  expect(bodies).toEqual([{ city: 'New City', expected_version: 2 }, { city: 'New City', expected_version: 2 }]);
});
