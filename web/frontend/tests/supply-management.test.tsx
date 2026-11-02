import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ProductSupplyForm } from "../src/components/products/ProductSupplyForm";
import { Products } from "../src/pages/Products";
import { SellThrough } from "../src/components/forecast/SellThrough";
import { InventoryInformation } from "../src/components/inventory/InventoryDetails";
import { AlertDetails } from "../src/components/alerts/AlertDetails";
import { PurchasingDetails } from "../src/components/purchasing/PurchasingDetails";
import type { Row } from "../src/types/api";
import type { Context } from "../src/types/context";

const product = { id:11, sku:"SYN-SUPPLY", city:"Melbourne", product_type:"eSIM", carrier:"SYN", supply_schema_ready:true };
const day="2025-10-31";
const ctx: Context={runId:"plan",origin:day,warehouseId:"1",itemId:"11",supplierId:"",productType:""};
const reply=(value:unknown,status=200)=>Promise.resolve({ok:status<300,status,json:async()=>value} as Response);
let rows:Row[], writes:Row[], reads:string[], blocked:boolean;
function fetcher(input:RequestInfo|URL,options?:RequestInit):Promise<Response> {
  const url=new URL(String(input),'http://localhost');reads.push(url.pathname+url.search);
  if (options?.method==='POST') {
    const body=JSON.parse(String(options.body));writes.push(body);
    if (blocked) return reply({error:{code:'version_conflict',message:'changed'}},409);
    rows.push({...body,id:rows.length+1,version:rows.length+1});return reply(rows.at(-1),201);
  }
  if(url.pathname.endsWith('supply-changes')) {
    const latest=rows.at(-1);const status=latest?.action==='stop'?(String(latest.effective_on)<=String(url.searchParams.get('as_of_date'))?'stopped':'scheduled_stop'):'active';
    return reply({items:[...rows].reverse(),total:rows.length,supply_version:rows.length,page:1,page_size:50,
      state:url.searchParams.get('as_of_date')?{supply_status:status,version:rows.length,stop_change_id:latest?.action==='stop'?latest.id:null,stop_on:latest?.effective_on}:null});
  }
  if(url.pathname.endsWith('/warehouses')) return reply({items:[],total:0});
  return reply({items:[{...product,supply_status:'active'}],total:51,page:1,page_size:50});
}
beforeEach(()=>{ rows=[];writes=[];reads=[];blocked=false;vi.spyOn(globalThis,'fetch').mockImplementation(fetcher); });
afterEach(()=>{ cleanup();vi.restoreAllMocks(); });

it('saves a seven-day stop with an impact preview, then cancels without rewriting history',async()=>{
  const saved=vi.fn();render(<ProductSupplyForm product={product} day={day} onDate={()=>{}} onSaved={saved} stock={{closing_qty:10,pending_qty:20}} />);
  const button=await screen.findByRole('button',{name:'Lên lịch ngừng nhập'});
  await waitFor(()=>expect(button).toBeEnabled());
  expect(screen.getByLabelText('Ngày ngừng nhập')).toHaveValue('2025-11-07');
  expect(screen.getByText(/SYN-SUPPLY · Melbourne/)).toBeVisible();
  fireEvent.change(screen.getByLabelText('Lý do thay đổi'),{target:{value:' Supplier notice '}});
  fireEvent.click(button);await waitFor(()=>expect(writes).toHaveLength(1));
  expect(writes[0]).toEqual({action:'stop',known_on:day,effective_on:'2025-11-07',reason:'Supplier notice',expected_version:0,target_change_id:null});
  expect(await screen.findByText(/Đã lưu tình trạng cung cấp/)).toBeVisible();
  const cancel=await screen.findByRole('button',{name:'Hủy lịch ngừng nhập'});
  fireEvent.change(screen.getByLabelText('Lý do thay đổi'),{target:{value:'Cancel notice'}});
  fireEvent.click(cancel);await waitFor(()=>expect(writes).toHaveLength(2));
  expect(writes[1]).toMatchObject({action:'cancel_stop',target_change_id:1,expected_version:1,effective_on:day});
  expect(rows).toHaveLength(2);expect(saved).toHaveBeenCalledTimes(2);
});

it('retains the reason on conflict and requires reload before resubmitting',async()=>{
  blocked=true;render(<ProductSupplyForm product={product} day={day} onDate={()=>{}} onSaved={()=>{}} />);
  const button=await screen.findByRole('button',{name:'Lên lịch ngừng nhập'});await waitFor(()=>expect(button).toBeEnabled());
  fireEvent.change(screen.getByLabelText('Lý do thay đổi'),{target:{value:'Keep this reason'}});
  fireEvent.click(button);await screen.findByRole('alert');
  expect(screen.getByLabelText('Lý do thay đổi')).toHaveValue('Keep this reason');expect(button).toBeDisabled();
  blocked=false;fireEvent.click(screen.getByRole('button',{name:'Tải lại tình trạng cung cấp'}));
  await waitFor(()=>expect(button).toBeEnabled());expect(writes).toHaveLength(1);
});

it('does not save without a simulation date or before seven days, and handles schema not ready',async()=>{
  const view=render(<ProductSupplyForm product={product} day="" onDate={()=>{}} onSaved={()=>{}} />);
  expect(await screen.findByText(/Chọn ngày mô phỏng trước/)).toBeVisible();
  expect(screen.getByRole('button',{name:'Lên lịch ngừng nhập'})).toBeDisabled();
  view.rerender(<ProductSupplyForm product={product} day={day} onDate={()=>{}} onSaved={()=>{}} />);
  await waitFor(()=>expect(screen.getByRole('button',{name:'Lên lịch ngừng nhập'})).toBeEnabled());
  fireEvent.change(screen.getByLabelText('Ngày ngừng nhập'),{target:{value:'2025-11-06'}});
  fireEvent.change(screen.getByLabelText('Lý do thay đổi'),{target:{value:'Notice'}});
  fireEvent.submit(screen.getByRole('form',{name:'Thay đổi tình trạng cung cấp'}));
  expect(writes).toHaveLength(0);
  view.rerender(<ProductSupplyForm product={{...product,supply_schema_ready:false}} day={day} onDate={()=>{}} onSaved={()=>{}} />);
  expect(screen.queryByRole('button',{name:'Lên lịch ngừng nhập'})).toBeNull();
});

it('prevents double submission and ignores completion after leaving the product',async()=>{
  let finish:((r:Response)=>void)|undefined;
  vi.mocked(fetch).mockImplementation((input,options)=>options?.method==='POST'?new Promise(r=>{finish=r;}):fetcher(input,options));
  const saved=vi.fn();const view=render(<ProductSupplyForm product={product} day={day} onDate={()=>{}} onSaved={saved} />);
  const button=await screen.findByRole('button',{name:'Lên lịch ngừng nhập'});await waitFor(()=>expect(button).toBeEnabled());
  fireEvent.change(screen.getByLabelText('Lý do thay đổi'),{target:{value:'Notice'}});
  const form=button.closest('form')!;fireEvent.submit(form);fireEvent.submit(form);
  expect(vi.mocked(fetch).mock.calls.filter(([,o])=>o?.method==='POST')).toHaveLength(1);
  view.unmount();await act(async()=>finish!({ok:true,status:201,json:async()=>({})} as Response));expect(saved).not.toHaveBeenCalled();
});

it('sends date/status filters to the server and resets pagination',async()=>{
  render(<Products onOpen={()=>{}} ctx={ctx} />);
  await waitFor(()=>expect(screen.getByLabelText('Tình trạng cung cấp')).toBeEnabled());
  fireEvent.click(await screen.findByRole('button',{name:'Sau →'}));
  await waitFor(()=>expect(reads.at(-1)).toContain('page=2'));
  fireEvent.change(screen.getByLabelText('Tình trạng cung cấp'),{target:{value:'stopped'}});
  await waitFor(()=>expect(reads.at(-1)).toContain('supply_status=stopped'));
  expect(reads.at(-1)).toContain('as_of_date=2025-10-31');expect(reads.at(-1)).toContain('page=1');
});

it('renders constrained sales and CSV, and gives a create-new-plan message for legacy data',async()=>{
  vi.mocked(fetch).mockImplementation(()=>reply({items:[{item_id:11,target_date:'2025-11-01',projected_sales_qty:2,forecast_demand_qty:4,unserved_demand_qty:2,closing_forecast:0,supply_status:'stopped'}],total:1}));
  const view=render(<SellThrough runId="plan" ctx={ctx} />);
  await screen.findByRole('columnheader',{name:'Dự kiến bán'});
  expect(screen.getByRole('link',{name:/Xuất CSV/})).toHaveAttribute('href',expect.stringContaining('/exports/sell_through?'));
  vi.mocked(fetch).mockImplementation(()=>reply({error:{code:'feature_not_in_run',message:'legacy'}},409));
  view.rerender(<SellThrough runId="old" ctx={ctx} />);
  expect(await screen.findByText(/Tạo kế hoạch mới để xem/)).toBeVisible();
  expect(screen.queryByRole('columnheader',{name:'Dự kiến bán'})).toBeNull();
});

it('labels stopped inventory and alerts without an order CTA or sufficient-stock badge',()=>{
  const row={sku:'SYN',replenishment_allowed:false,supply_status:'stopped',sell_through_state:'waiting_receipts',needs_replenishment:false,recommended_qty:10};
  const open=vi.fn();const view=render(<InventoryInformation focused={row} onItem={open} />);
  expect(screen.queryByText('Đủ tồn')).toBeNull();expect(screen.getByText('Chờ lô đang về')).toBeVisible();
  expect(screen.queryByRole('button',{name:/Xem đề xuất nhập/})).toBeNull();
  view.unmount();const alertView=render(<AlertDetails focused={{...row,alert_type:'below_rop',state:'low_stock',explanation:{}}} onClose={()=>{}} onItem={open} />);
  expect(screen.queryByRole('button',{name:'Xem kế hoạch nhập'})).toBeNull();
  alertView.unmount();render(<PurchasingDetails focused={{...row,id:1,status:'pending',ordered_qty:20,eta:'2025-11-04'}} view="incoming" onClose={()=>{}} selectView={()=>{}} />);
  expect(screen.getByText('Đã ngừng nhập')).toBeVisible();
  expect(screen.getByText(/Lô đã đặt vẫn nhận đúng ETA/)).toBeVisible();
});


it('opens supply again with the original stop target and current version',async()=>{
  rows=[{id:7,version:1,action:'stop',known_on:'2025-10-24',effective_on:day}];
  render(<ProductSupplyForm product={product} day={day} onDate={()=>{}} onSaved={()=>{}} />);
  const button=await screen.findByRole('button',{name:'Mở nhập lại'});await waitFor(()=>expect(button).toBeEnabled());
  expect(screen.queryByLabelText('Ngày ngừng nhập')).toBeNull();
  fireEvent.change(screen.getByLabelText('Lý do thay đổi'),{target:{value:'Supply resumed'}});
  fireEvent.click(button);await waitFor(()=>expect(writes).toHaveLength(1));
  expect(writes[0]).toMatchObject({action:'resume',known_on:day,effective_on:day,target_change_id:7,expected_version:1});
});
