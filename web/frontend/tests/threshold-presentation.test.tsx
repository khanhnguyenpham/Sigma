import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { Alerts } from "../src/pages/Alerts";
import { Overview } from "../src/pages/Overview";
import { InventoryDetails } from "../src/components/inventory/InventoryDetails";
import type { Context } from "../src/types/context";
import type { Run } from "../src/types/api";

beforeEach(() => {
  vi.stubGlobal("ResizeObserver", class { observe() {} unobserve() {} disconnect() {} });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });
const ctx: Context = { runId:"plan", origin:"2025-10-31", warehouseId:"1", itemId:"", supplierId:"", productType:"" };
const run = { id:"plan", kind:"alert_replay", status:"complete", result_summary:{
  alert_metrics:{ early_rate:.34, early_numerator:34, event_denominator:100, precision:.5, recall:.6, excluded_count:2 },
  threshold_metrics:{ TP:1, FP:2, FN:3, TN:4, event_denominator:4, signal_count:3, evaluated_count:10, excluded_count:5, precision:1/3, recall:.25, date_mae:1 },
} } as unknown as Run;
const threshold = { id:1, item_id:7, warehouse_id:1, sku:"SYNTHETIC-SKU", product_type:"eSIM", carrier:"DemoNet", destination_country:"DemoLand",
  alert_type:"projected_below_rop", state:"threshold_warning", as_of_date:ctx.origin,
  predicted_threshold_date:"2025-11-01", predicted_depletion_date:null, lead_days:null, evaluation_class:"TP",
  explanation:{ origin_on_hand:21, policy:{ safety_mode:"volatility", safety_lookback_days:28, safety_factor:0, rop_mode:"fixed", warning_horizon_days:7 },
    thresholds:{ rop:20, ss:0 }, projection:[{ date:"2025-11-01", closing_forecast:19, receipts_qty:0 }],
    threshold_evaluation:{ actual_threshold_date:"2025-11-02" } } };
const depletion = { ...threshold, id:2, alert_type:"depletion", state:"early", predicted_threshold_date:null, predicted_depletion_date:"2025-11-09", lead_days:9 };
const workspace = { context:{}, summary:{ warning_items:1, projected_below_rop_items:1, urgent_items:0, low_stock_items:0, item_count:1, inventory_available:true }, attention:[], incoming:[], route_stock:[] };
const response = (data: unknown) => Promise.resolve({ ok:true, json:async()=>data } as Response);
function mockResults(input: RequestInfo | URL) {
  const url = String(input);
  if (url.includes("/workspace?")) return response(workspace);
  if (url.includes("/alert-opportunities")) return response({});
  const filtered = url.includes("alert_type=projected_below_rop");
  return response({ items:filtered ? [threshold] : [threshold,depletion], total:filtered ? 1 : 51, page:1, page_size:50 });
}

it("filters threshold signals and exports the same run, origin, type and state with pagination reset", async () => {
  const calls: string[] = [];
  vi.spyOn(globalThis,"fetch").mockImplementation((input) => { calls.push(String(input)); return mockResults(input); });
  render(<Alerts run={run} ctx={ctx} />);
  await screen.findAllByText("SYNTHETIC-SKU");
  fireEvent.click(screen.getByRole("button",{name:"Sau →"}));
  await waitFor(()=>expect(screen.getByText("Trang 2")).toBeVisible());
  fireEvent.change(screen.getByLabelText("Loại tín hiệu cảnh báo"),{target:{value:"projected_below_rop"}});
  fireEvent.change(screen.getByLabelText("Trạng thái cảnh báo"),{target:{value:"threshold_warning"}});
  await waitFor(()=>expect(calls.some(u=>u.includes("alert_type=projected_below_rop") && u.includes("state=threshold_warning") && u.includes("page=1"))).toBe(true));
  await screen.findByText("SYNTHETIC-SKU");
  const href = screen.getByRole("link",{name:/Xuất CSV/}).getAttribute("href")!;
  const url = new URL(href,"http://localhost");
  expect(url.pathname).toBe("/api/v1/runs/plan/exports/alerts");
  expect(Object.fromEntries(url.searchParams)).toMatchObject({ as_of_date:ctx.origin, warehouse_id:"1", alert_type:"projected_below_rop", state:"threshold_warning", page:"1" });
  expect(screen.queryByText("2025-11-09")).toBeNull();
  expect(screen.getByRole("columnheader",{name:"Xuống ROP dự kiến"})).toBeVisible();
  expect(screen.getByRole("columnheader",{name:"Cạn dự kiến"})).toBeVisible();
});

it("shows origin ROP and N with separate threshold/depletion dates and a UTC projection table", async () => {
  vi.spyOn(globalThis,"fetch").mockImplementation(mockResults);
  render(<Alerts run={run} ctx={ctx} />);
  const labels = await screen.findAllByText("SYNTHETIC-SKU");
  fireEvent.click(labels[0]);
  const dialog=within(screen.getByRole("dialog"));
  expect(dialog.getByText("ROP tại quyết định").nextElementSibling).toHaveTextContent("20");
  expect(dialog.getByText("N ngày nhìn trước ROP").nextElementSibling).toHaveTextContent("7");
  expect(dialog.getByText("Xuống ROP dự kiến").nextElementSibling).toHaveTextContent("2025-11-01");
  expect(dialog.getByText("Cạn dự kiến").nextElementSibling).toHaveTextContent("—");
  expect(dialog.getByText(/Tồn tại quyết định chưa dưới ROP/)).toBeVisible();
  fireEvent.click(dialog.getByText("Bảng tồn dự kiến theo ngày UTC"));
  expect(dialog.getByRole("columnheader",{name:"Tồn cuối ngày dự kiến"})).toBeVisible();
  expect(dialog.getByRole("cell",{name:"19"})).toBeVisible();
  fireEvent.click(dialog.getByText("Thông tin đánh giá lịch sử"));
  expect(dialog.getByText("Ngày xuống ROP trong replay").nextElementSibling).toHaveTextContent("2025-11-02");
  expect(dialog.queryByText("Ngày cạn trong replay")).toBeNull();
  fireEvent.keyDown(document,{key:"Escape"});
  expect(screen.queryByRole("dialog")).toBeNull();
});

it("keeps both whole-run metric denominators unchanged when the signal table is filtered", async () => {
  vi.spyOn(globalThis,"fetch").mockImplementation(mockResults);
  render(<Alerts run={run} ctx={ctx} />);
  await screen.findAllByText("SYNTHETIC-SKU");
  fireEvent.click(screen.getByText("Đánh giá lịch sử & độ tin cậy cảnh báo"));
  fireEvent.click(screen.getByText("Đánh giá xuống ROP · riêng ngày cạn"));
  expect(screen.getByText("Báo sớm ≥7 ngày").closest("article")).toHaveTextContent("34/100");
  expect(screen.getByText("Sự kiện xuống ROP").closest("article")).toHaveTextContent("4");
  fireEvent.change(screen.getByLabelText("Loại tín hiệu cảnh báo"),{target:{value:"projected_below_rop"}});
  await screen.findByText("SYNTHETIC-SKU");
  expect(screen.getByText("Báo sớm ≥7 ngày").closest("article")).toHaveTextContent("34/100");
  expect(screen.getByText("Sự kiện xuống ROP").closest("article")).toHaveTextContent("4");
  expect(screen.getByText(/không cộng vào tỷ lệ báo trước ngày cạn/)).toBeVisible();
});

it("hides the old warning drawer and counts immediately when context changes", async () => {
  vi.spyOn(globalThis,"fetch").mockImplementation((input)=>String(input).includes("/new/")?new Promise(()=>{}):mockResults(input));
  const view=render(<Alerts run={run} ctx={ctx} />);
  fireEvent.click((await screen.findAllByText("SYNTHETIC-SKU"))[0]);
  expect(screen.getByRole("dialog")).toBeVisible();
  view.rerender(<Alerts run={{...run,id:"new",result_summary:{}}} ctx={{...ctx,runId:"new"}} />);
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(screen.queryByText("SYNTHETIC-SKU")).toBeNull();
  expect(screen.getByText("Mặt hàng có cảnh báo").closest("article")).toHaveTextContent("—");
  expect(screen.queryByText("Đánh giá xuống ROP · riêng ngày cạn")).toBeNull();
});

it("shows one warning item on Overview even when that item has two alert signals", async () => {
  vi.spyOn(globalThis,"fetch").mockImplementation(()=>response(workspace));
  render(<Overview run={run} ctx={ctx} runs={[run]} onRun={()=>{}} onCreate={()=>{}} onNavigate={()=>{}} onItem={()=>{}} />);
  await waitFor(()=>expect(screen.getByText("Cảnh báo cần xử lý").closest("article")).toHaveTextContent("1"));
  expect(screen.getByText("Mỗi mặt hàng tính một lần, gồm ngưỡng nhập và nguy cơ cạn")).toBeVisible();
});

it("explains a fixed inventory ROP without displaying the forecast max formula", () => {
  render(<InventoryDetails focused={{sku:"FIXED",rop_mode:"fixed",configured_rop_floor:20,rop_forecast:99,ss:5,safety_mode:"volatility",safety_lookback_days:28,safety_factor:0,warning_horizon_days:7}} onClose={()=>{}} />);
  fireEvent.click(screen.getByText("Chi tiết sổ tồn & cách tính"));
  expect(screen.getByText("ROP cố định = 20; không cộng SS lần nữa")).toBeVisible();
  expect(screen.queryByText(/ROP = max/)).toBeNull();
});

it("explains a fixed quantity per order while keeping the target only as a reference", () => {
  render(<InventoryDetails focused={{sku:"LOT",fixed_order_qty:25,moq:null,target_stock:110,inventory_position:80,recommended_qty:25}} onClose={()=>{}} />);
  expect(screen.getByText("Lượng nhập mỗi lần").nextElementSibling).toHaveTextContent("25");
  fireEvent.click(screen.getByText("Chi tiết sổ tồn & cách tính"));
  expect(screen.getByText(/Q = 25 đơn vị mỗi lần, không tự tăng để bù đủ S/)).toBeVisible();
  expect(screen.queryByText("MOQ của phương án cũ")).toBeNull();
});

it("labels historical MOQ explicitly without inventing a fixed quantity", () => {
  render(<InventoryDetails focused={{sku:"OLD",moq:10}} onClose={()=>{}} />);
  expect(screen.getByText("MOQ của phương án cũ").nextElementSibling).toHaveTextContent("10");
  expect(screen.queryByText("Lượng nhập mỗi lần")).toBeNull();
});

it("keeps undefined threshold ratios as a dash when there are no events", async () => {
  vi.spyOn(globalThis,"fetch").mockImplementation(mockResults);
  const emptyRun={...run,result_summary:{threshold_metrics:{TP:0,FP:0,FN:0,TN:1,event_denominator:0,signal_count:0,evaluated_count:1,excluded_count:0,precision:null,recall:null,date_mae:null}}};
  render(<Alerts run={emptyRun} ctx={ctx} />);
  fireEvent.click(screen.getByText("Đánh giá xuống ROP · riêng ngày cạn"));
  expect(screen.getByText("Precision xuống ROP").closest("article")).toHaveTextContent("—");
  expect(screen.getByText("Recall xuống ROP").closest("article")).toHaveTextContent("—");
  expect(screen.queryByText(/NaN|Infinity/)).toBeNull();
});
