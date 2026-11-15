import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Recommendations } from "../src/operations/Recommendations";
afterEach(()=>{cleanup();vi.restoreAllMocks();});
const reply=(items:unknown[])=>({ok:true,status:200,json:async()=>({items,total:items.length,page:1,page_size:25,origin:"2026-11-15",forecast_origin:null,captured_at:"2026-11-15T00:00:00Z",forecast_options:[]})}) as Response;
it("does not present a missing prediction as zero purchase or safe stock",async()=>{
  vi.spyOn(globalThis,"fetch").mockResolvedValue(reply([{item_id:1,sku:"SIM",on_hand_qty:3,lead_time_days:30,decision:"blocked",reason:"forecast_horizon_short",recommended_qty:null,rop:null}]));
  render(<Recommendations/>);
  expect(await screen.findByText("Chưa đủ điều kiện")).toBeVisible();
  expect(screen.getByText(/Cần dự báo dài hơn/)).toBeVisible();
  expect(screen.getByRole("button",{name:"Xem từng ngày"})).toBeDisabled();
});
it("shows early shortage before a normal new delivery as an action warning",async()=>{
  vi.spyOn(globalThis,"fetch").mockResolvedValue(reply([{item_id:1,sku:"SIM",on_hand_qty:0,lead_time_days:7,decision:"order",reason:"fixed_lot_policy",recommended_qty:15,rop:18,safety_stock:4,shortage_before_new_eta:true,projection:[{date:"2026-11-16",demand:2,receipts_qty:0,closing_qty:0,shortage_qty:2}]}]));
  render(<Recommendations/>);
  fireEvent.click(await screen.findByRole("button",{name:"Xem từng ngày"}));
  expect(screen.getByText(/Đặt thông thường chưa giải quyết được/)).toBeVisible();
  expect(screen.getByRole("cell",{name:"2026-11-16"})).toBeVisible();
});
