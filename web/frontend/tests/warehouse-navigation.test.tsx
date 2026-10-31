import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import App from "../src/App";

const warehouses = [
  { id: 1, city: "Sydney", destination_country: "Australia", carrier: "Optus" },
  { id: 2, city: "Sydney", destination_country: "Australia", carrier: "Telstra" },
  { id: 3, city: "Tokyo", destination_country: "Japan", carrier: "NTT Docomo" },
];
const stocks = warehouses.map((w, index) => ({ ...w, warehouse_id: w.id, item_count: index ? 20 : 63,
  on_hand_units: index === 1 ? 0 : 100, low_stock_items: 2, replenish_items: 2, recommended_units: 15 }));
const run = { id: "plan", kind: "stock_projection", status: "complete", as_of_date: "2025-10-31",
  result_summary: { inventory_available: true }, forecast_run_id: "forecast" };
const item = { id: 11, item_id: 11, warehouse_id: 1, city: "Sydney", carrier: "Optus", destination_country: "Australia",
  sku: "SYNTHETIC-SKU", product_type: "physical_SIM", closing_qty: 7, rop: 20, recommended_qty: 10, needs_replenishment: true };
const response = (body: unknown, status = 200) => Promise.resolve({ ok: status === 200, status, json: async () => body } as Response);
const calls: string[] = [];
function read(input: RequestInfo | URL) {
  const url = new URL(String(input), "http://localhost");
  calls.push(url.pathname + url.search);
  if (url.pathname.endsWith('/runs')) return response({ items: [run], total: 1 });
  if (url.pathname.endsWith('/warehouses')) return response({ items: warehouses, total: 3 });
  if (url.pathname.endsWith('/suppliers')) return response({ items: warehouses.map((w) => ({ id: w.id + 100, carrier: w.carrier })), total: 3 });
  if (url.pathname.endsWith('/items')) return response({ items: [item], total: 1 });
  if (url.pathname.endsWith('/workspace')) {
    const selected = url.searchParams.get('warehouse_id');
    const rows = stocks.filter((s) => !selected || String(s.warehouse_id) === selected);
    return response({ context: {}, summary: { item_count: rows.reduce((n, s) => n + s.item_count, 0),
      on_hand_units: rows.reduce((n, s) => n + s.on_hand_units, 0) }, warehouse_stock: rows, attention: [], incoming: [], route_stock: [] });
  }
  return response({ items: [item], total: url.searchParams.has('product_type') ? 1 : 51,
    page: Number(url.searchParams.get('page') ?? 1), page_size: 50, summary: {}, context: {} });
}
beforeEach(() => {
  calls.length = 0;
  history.replaceState(null, '', '/?run_id=plan&origin=2025-10-31#inventory');
  vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
  vi.spyOn(globalThis, 'fetch').mockImplementation(read);
  vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); history.replaceState(null, '', '/'); });

it('starts with distinct warehouse cards named only by city and complete warehouse totals', async () => {
  render(<App />);
  const optus = await screen.findByRole('button', { name: 'Mở kho Sydney tại Australia, nhà mạng Optus' });
  await waitFor(() => expect(within(optus).getByText('63')).toBeVisible());
  expect(screen.getAllByRole('heading', { level: 3, name: 'Sydney' })).toHaveLength(2);
  expect(within(optus).getByText('Optus')).toBeVisible();
  expect(screen.queryByRole('heading', { name: 'Sydney · Optus' })).toBeNull();
  expect(calls.some((u) => u.includes('/inventory?'))).toBe(false);
  expect(screen.queryByLabelText('SKU')).toBeNull();
  const telstra = screen.getByRole('button', { name: 'Mở kho Sydney tại Australia, nhà mạng Telstra' });
  expect(within(telstra).getByText('0')).toBeVisible();
  fireEvent.change(screen.getByLabelText('Quốc gia của kho'), { target: { value: 'Japan' } });
  expect(screen.getByRole('heading', { level: 3, name: 'Tokyo' })).toBeVisible();
  expect(screen.queryByRole('heading', { level: 3, name: 'Sydney' })).toBeNull();
  fireEvent.change(screen.getByLabelText('Tìm kho'), { target: { value: 'Sydney' } });
  expect(screen.getByText(/Không có bản ghi phù hợp/)).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Xóa bộ lọc kho' }));
  fireEvent.change(screen.getByLabelText('Nhà mạng của kho'), { target: { value: 'Telstra' } });
  expect(screen.getAllByRole('heading', { level: 3 })).toHaveLength(1);
  expect(screen.getByRole('button', { name: 'Mở kho Sydney tại Australia, nhà mạng Telstra' })).toBeVisible();
});

it('opens one warehouse, scopes filters and CSV, resets pagination and preserves the warehouse in purchasing', async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole('button', { name: 'Mở kho Sydney tại Australia, nhà mạng Optus' }));
  await screen.findByRole('heading', { level: 1, name: 'Sydney' });
  await screen.findByText('SYNTHETIC-SKU');
  expect(location.search).toContain('warehouse_id=1');
  expect(calls.filter((u) => u.includes('/inventory?')).every((u) => u.includes('warehouse_id=1'))).toBe(true);
  fireEvent.click(screen.getByRole('button', { name: 'Sau →' }));
  await waitFor(() => expect(screen.getByText('Trang 2')).toBeVisible());
  fireEvent.change(screen.getByLabelText('Nhà mạng trong kho'), { target: { value: '101' } });
  fireEvent.change(screen.getByLabelText('Loại sản phẩm trong kho'), { target: { value: 'physical_SIM' } });
  await waitFor(() => expect(screen.getByText('Trang 1')).toBeVisible());
  fireEvent.change(screen.getByLabelText('SKU trong kho'), { target: { value: '11' } });
  const csv = new URL(screen.getByRole('link', { name: /Xuất CSV/ }).getAttribute('href')!, 'http://localhost');
  expect(Object.fromEntries(csv.searchParams)).toMatchObject({ warehouse_id: '1', supplier_id: '101',
    product_type: 'physical_SIM', item_id: '11', page: '1', date_from: '2025-10-31', date_to: '2025-10-31' });
  const actions = screen.getByRole('heading', { level: 1, name: 'Sydney' }).closest('.page-heading')!;
  fireEvent.click(within(actions as HTMLElement).getByRole('button', { name: 'Nhập hàng' }));
  await screen.findByRole('heading', { name: 'Kế hoạch nhập hàng' });
  expect(location.hash).toBe('#replenishment');
  expect(screen.getByLabelText('Kho / tuyến')).toHaveValue('1');
  expect(within(screen.getByLabelText('Kho / tuyến')).getAllByRole('option', { name: 'Sydney' })).toHaveLength(2);
  await waitFor(() => expect(calls.some((u) => u.includes('/purchasing?') && u.includes('warehouse_id=1'))).toBe(true));
});

it('supports the directory breadcrumb, browser Back and reloading a warehouse deep link', async () => {
  let view = render(<App />);
  fireEvent.click(await screen.findByRole('button', { name: 'Mở kho Sydney tại Australia, nhà mạng Telstra' }));
  await screen.findByRole('heading', { level: 1, name: 'Sydney' });
  expect(location.search).toContain('warehouse_id=2');
  view.unmount();
  view = render(<App />);
  await screen.findByRole('heading', { level: 1, name: 'Sydney' });
  fireEvent.click(screen.getByRole('button', { name: 'Danh sách kho' }));
  await screen.findByRole('button', { name: 'Mở kho Sydney tại Australia, nhà mạng Telstra' });
  expect(location.search).not.toContain('warehouse_id');
  act(() => history.back());
  await waitFor(() => expect(location.search).toContain('warehouse_id=2'));
  expect(await screen.findByRole('heading', { level: 1, name: 'Sydney' })).toBeVisible();
  view.unmount();
});

it('opens operational daily demand for the warehouse while keeping the monthly tab available', async () => {
  render(<App />);
  fireEvent.click(await screen.findByRole('button', { name: 'Mở kho Sydney tại Australia, nhà mạng Optus' }));
  const heading = await screen.findByRole('heading', { level: 1, name: 'Sydney' });
  fireEvent.click(within(heading.closest('.page-heading')!).getByRole('button', { name: 'Dự báo nhu cầu' }));
  await screen.findByRole('heading', { name: 'Ngày phân bổ từ tổng tuần' }, { timeout: 5000 });
  expect(screen.getByRole('button', { name: 'Phân bổ theo ngày' })).toHaveClass('active');
  expect(screen.getByRole('button', { name: 'Tổng 30 ngày' })).toBeVisible();
  await waitFor(() => expect(calls.some((u) => u.includes('/forecasts/items?') && u.includes('warehouse_id=1') && u.includes('aggregate=route_day'))).toBe(true));
});
