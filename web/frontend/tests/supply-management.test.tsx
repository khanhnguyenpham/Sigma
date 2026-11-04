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

const product={id:11,sku:"SYN-SUPPLY",city:"Melbourne",product_type:"eSIM",carrier:"SYN",supply_schema_ready:true,trade_schema_ready:true};
const day="2025-10-31",fp="a".repeat(64);
const ctx:Context={runId:"plan",origin:day,warehouseId:"1",itemId:"11",supplierId:"",productType:""};
const reply=(value:unknown,status=200)=>Promise.resolve({ok:status<300,status,json:async()=>value} as Response);
let rows:Row[],writes:Row[],previews:Row[],reads:string[],blocked:boolean,refreshFailure:boolean;
function fetcher(input:RequestInfo|URL,options?:RequestInit):Promise<Response>{
  const url=new URL(String(input),'http://localhost');if(url.searchParams.has('v'))return reply({error:{code:'invalid_input',message:'Unexpected query field'}},422);reads.push(url.pathname+url.search);
  if(options?.method==='POST'){
    const body=JSON.parse(String(options.body));
    if(url.pathname.endsWith('internal-stop-preview')){previews.push(body);return reply({preview_fingerprint:fp,impact:{inventory_complete:false},after:{internal_status:'stopped',provider_status:'stopped',replenishment_allowed:false,sales_allowed:false}});}
    writes.push(body);if(blocked)return reply({error:{code:'preview_stale',message:'changed'}},409);
    rows.push({...body,id:rows.length+1,version:rows.length+1});return reply(rows.at(-1),201);
  }
  if(url.pathname.endsWith('supply-changes')){
    if(refreshFailure && writes.length)return reply({error:{code:'database_unavailable',message:'offline'}},503);
    const asof=url.searchParams.get('as_of_date'),visible=rows.filter(r=>String(r.known_on)<=String(asof)),latest=visible.at(-1);
    const status=latest?.action==='stop'?(String(latest.effective_on)<=String(asof)?'stopped':'scheduled_stop'):'active';
    return reply({items:[...rows].reverse(),total:rows.length,supply_version:rows.length,page:1,page_size:50,state:asof?{supply_status:status,version:visible.length,stop_change_id:latest?.action==='stop'?latest.id:null}:null});
  }
  if(url.pathname.endsWith('/warehouses'))return reply({items:[],total:0});
  return reply({items:[{...product,supply_status:'active',internal_status:'active',provider_status:'clear'}],total:51,page:1,page_size:50});
}
beforeEach(()=>{rows=[];writes=[];previews=[];reads=[];blocked=false;refreshFailure=false;vi.spyOn(globalThis,'fetch').mockImplementation(fetcher);});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
async function preview(){const button=await screen.findByRole('button',{name:'Xem tác động'});await waitFor(()=>expect(button).toBeEnabled());fireEvent.change(screen.getByLabelText('Lý do thay đổi'),{target:{value:' Internal decision '}});fireEvent.click(button);await waitFor(()=>expect(screen.getByRole('button',{name:/^Lưu /})).toBeEnabled());}

it('previews and saves a same-day internal stop, invalidating the preview on edit',async()=>{
  const saved=vi.fn();render(<ProductSupplyForm product={product} day={day} onDate={()=>{}} onSaved={saved} />);
  expect(screen.getByLabelText('Ngày hiệu lực UTC')).toHaveValue(day);
  await preview();expect(writes).toHaveLength(0);
  fireEvent.change(screen.getByLabelText('Lý do thay đổi'),{target:{value:'Changed decision'}});
  expect(screen.getByRole('button',{name:'Lưu ngừng nhập nội bộ'})).toBeDisabled();
  fireEvent.click(screen.getByRole('button',{name:'Xem tác động'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Lưu ngừng nhập nội bộ'})).toBeEnabled());
  fireEvent.click(screen.getByRole('button',{name:'Lưu ngừng nhập nội bộ'}));await waitFor(()=>expect(saved).toHaveBeenCalledTimes(1));
  expect(writes[0]).toEqual({action:'stop',known_on:day,effective_on:day,reason:'Changed decision',expected_version:0,target_change_id:null,preview_fingerprint:fp});
  expect(screen.getByText(/Vẫn bán tồn được phép bán/)).toBeVisible();
});

it.each([['cancel_stop','2025-11-07','Lưu hủy lịch ngừng nhập'],['resume',day,'Lưu mở nhập lại nội bộ']])('uses a separate %s action without changing its meaning on reload',async(action,effective,title)=>{
  rows=[{id:7,version:1,action:'stop',known_on:'2025-10-24',effective_on:effective}];
  render(<ProductSupplyForm product={product} day={day} action={action as 'cancel_stop'|'resume'} onDate={()=>{}} onSaved={()=>{}} />);
  await preview();expect(screen.getByLabelText('Ngày hiệu lực UTC')).toHaveAttribute('readonly');
  expect(screen.getByText(/Không được bán mới/)).toBeVisible();
  fireEvent.click(screen.getByRole('button',{name:title}));await waitFor(()=>expect(writes).toHaveLength(1));
  expect(writes[0]).toMatchObject({action,known_on:day,effective_on:day,target_change_id:7,expected_version:1,preview_fingerprint:fp});
});

it('keeps the reason on conflict and reloads without automatically retrying the mutation',async()=>{
  blocked=true;render(<ProductSupplyForm product={product} day={day} onDate={()=>{}} onSaved={()=>{}} />);await preview();
  fireEvent.click(screen.getByRole('button',{name:'Lưu ngừng nhập nội bộ'}));await screen.findByRole('alert');
  expect(screen.getByLabelText('Lý do thay đổi')).toHaveValue(' Internal decision ');
  expect(screen.getByRole('button',{name:'Xem tác động'})).toBeDisabled();
  blocked=false;fireEvent.click(screen.getByRole('button',{name:'Tải lại dữ liệu'}));
  await waitFor(()=>expect(screen.getByRole('button',{name:'Xem tác động'})).toBeEnabled());
  expect(writes).toHaveLength(1);expect(screen.getByRole('button',{name:'Lưu ngừng nhập nội bộ'})).toBeDisabled();
});

it('does not fill a cleared date on retry, rejects backdated internal effect and respects schema readiness',async()=>{
  const view=render(<ProductSupplyForm product={product} day={day} onDate={()=>{}} onSaved={()=>{}} />);
  await waitFor(()=>expect(screen.getByRole('button',{name:'Xem tác động'})).toBeEnabled());
  fireEvent.change(screen.getByLabelText('Ngày ghi nhận UTC'),{target:{value:''}});
  window.dispatchEvent(new Event('sigma:refresh'));await waitFor(()=>expect(screen.getByRole('button',{name:'Xem tác động'})).toBeDisabled());
  expect(screen.getByLabelText('Ngày ghi nhận UTC')).toHaveValue('');
  fireEvent.change(screen.getByLabelText('Ngày ghi nhận UTC'),{target:{value:day}});
  await waitFor(()=>expect(screen.getByRole('button',{name:'Xem tác động'})).toBeEnabled());
  fireEvent.change(screen.getByLabelText('Ngày hiệu lực UTC'),{target:{value:'2025-10-30'}});
  fireEvent.change(screen.getByLabelText('Lý do thay đổi'),{target:{value:'Reason'}});fireEvent.click(screen.getByRole('button',{name:'Xem tác động'}));
  expect(previews).toHaveLength(0);
  view.rerender(<ProductSupplyForm product={{...product,trade_schema_ready:false}} day={day} onDate={()=>{}} onSaved={()=>{}} />);
  expect(screen.getByRole('button',{name:'Xem tác động'})).toBeDisabled();expect(await screen.findByText(/Chức năng mới chưa được bật/)).toBeVisible();
});

it('blocks double saves and ignores callbacks after leaving the dialog',async()=>{
  let finish:((r:Response)=>void)|undefined;
  vi.mocked(fetch).mockImplementation((input,options)=>options?.method==='POST' && String(input).includes('/supply-changes')?new Promise(r=>{finish=r;}):fetcher(input,options));
  const saved=vi.fn(),view=render(<ProductSupplyForm product={product} day={day} onDate={()=>{}} onSaved={saved} />);await preview();
  const form=screen.getByRole('form',{name:'Ngừng nhập nội bộ'});fireEvent.submit(form);fireEvent.submit(form);
  expect(vi.mocked(fetch).mock.calls.filter(([p,o])=>o?.method==='POST' && String(p).includes('/supply-changes'))).toHaveLength(1);
  view.unmount();await act(async()=>finish!({ok:true,status:201,json:async()=>({id:1})} as Response));expect(saved).not.toHaveBeenCalled();
});

it('acknowledges a successful write even if refresh fails, and only retries the GET',async()=>{
  const saved=vi.fn();render(<ProductSupplyForm product={product} day={day} onDate={()=>{}} onSaved={saved} />);await preview();refreshFailure=true;
  fireEvent.click(screen.getByRole('button',{name:'Lưu ngừng nhập nội bộ'}));await screen.findByRole('alert');
  expect(screen.getByText(/Chưa tải lại được dữ liệu/)).toBeVisible();expect(writes).toHaveLength(1);
  refreshFailure=false;fireEvent.click(screen.getByRole('button',{name:'Tải lại dữ liệu'}));await waitFor(()=>expect(saved).toHaveBeenCalledOnce());expect(writes).toHaveLength(1);
});

it('sends independent internal/provider filters and resets pagination',async()=>{
  render(<Products onOpen={()=>{}} ctx={ctx} />);await waitFor(()=>expect(screen.getByLabelText('Trạng thái')).toBeEnabled());
  fireEvent.click(await screen.findByRole('button',{name:'Sau →'}));await waitFor(()=>expect(reads.at(-1)).toContain('page=2'));
  fireEvent.change(screen.getByLabelText('Trạng thái nhập'),{target:{value:'stopped'}});fireEvent.change(screen.getByLabelText('Trạng thái'),{target:{value:'stopped'}});
  await waitFor(()=>expect(reads.at(-1)).toContain('provider_status=stopped'));expect(reads.at(-1)).toContain('internal_status=stopped');expect(reads.at(-1)).toContain('page=1');
});

it('renders saved constrained quantities and CSV, with explicit legacy availability',async()=>{
  vi.mocked(fetch).mockImplementation(()=>reply({context:{trade_lifecycle_profile:'internal_provider_trade_v2'},items:[{item_id:11,target_date:'2025-11-01',projected_sales_qty:0,forecast_demand_qty:4,unserved_stock_qty:0,sales_blocked_qty:4,closing_blocked:10,closing_sellable:0}],total:1}));
  const view=render(<SellThrough runId="plan" ctx={ctx} />);await screen.findByRole('columnheader',{name:'Bị nhà mạng chặn'});
  expect(screen.getByRole('link',{name:/Xuất CSV/})).toHaveAttribute('href',expect.stringContaining('/exports/sell_through?'));
  vi.mocked(fetch).mockImplementation(()=>reply({error:{code:'feature_not_in_run',message:'legacy'}},409));view.rerender(<SellThrough runId="old" ctx={ctx} />);
  expect(await screen.findByText(/Tạo kế hoạch mới để xem/)).toBeVisible();expect(screen.queryByRole('columnheader',{name:'Dự kiến bán'})).toBeNull();
});

it('does not invite replenishment for provider blocks or caps while retaining lot history',()=>{
  const row={sku:'SYN',trade_lifecycle_profile:'internal_provider_trade_v2',internal_status:'active',provider_status:'stopped',sales_allowed:false,replenishment_allowed:false,needs_replenishment:false,recommended_qty:10,q_final:0,cap_reason:'provider_blocked',total_qty:10,blocked_qty:10,sellable_qty:0};
  const open=vi.fn(),view=render(<InventoryInformation focused={row} onItem={open} />);expect(screen.queryByText('Đủ tồn')).toBeNull();expect(screen.queryByRole('button',{name:/Xem đề xuất nhập/})).toBeNull();view.unmount();
  const alert=render(<AlertDetails focused={{...row,alert_type:'below_rop',state:'low_stock',explanation:{}}} onClose={()=>{}} onItem={open} />);expect(screen.queryByRole('button',{name:'Xem kế hoạch nhập'})).toBeNull();alert.unmount();
  render(<PurchasingDetails focused={{...row,id:1,status:'ordered',ordered_qty:20,eta:'2025-11-04',needs_supplier_action:true}} view="incoming" onClose={()=>{}} selectView={()=>{}} />);expect(screen.getByText(/Cần xử lý với nhà cung cấp/)).toBeVisible();
});
