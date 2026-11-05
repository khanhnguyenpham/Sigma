import { act,cleanup,fireEvent,render,screen,waitFor,within } from "@testing-library/react";
import { beforeEach,afterEach,expect,it,vi } from "vitest";
import { ProviderNoticeForm } from "../src/components/products/ProviderNoticeForm";
import { ProviderNotices } from "../src/pages/ProviderNotices";
import { ProductDetail } from "../src/pages/Products";
import { RunForm } from "../src/components/configuration/RunForm";
import { SellThrough } from "../src/components/forecast/SellThrough";
import { contextUrl,readContext,navigationUrl } from "../src/utils/url";
import type { Row,Run } from "../src/types/api";

const day='2025-10-31',fp='b'.repeat(64),ctx={runId:'plan',origin:day,warehouseId:'1',itemId:'11',supplierId:'',productType:''};

it('shows separate frozen purchase and sale rights in projected rows, with aggregate and legacy fallbacks',async()=>{
  vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({items:[
    {target_date:'2025-11-01',supply_status:'active',internal_status:'active',provider_status:'stopped',replenishment_allowed:false,sales_allowed:false},
    {target_date:'2025-11-02',supply_status:'stopped',internal_status:'stopped',provider_status:'clear',replenishment_allowed:false,sales_allowed:true},
    {target_date:'2025-11-03',supply_status:'active'}],total:3,context:{trade_lifecycle_profile:'internal_provider_trade_v2'}}),{status:200}));
  const view=render(<SellThrough runId="plan" ctx={{...ctx,warehouseId:'',itemId:''}} />);
  await screen.findByRole('columnheader',{name:'Quyền mua bán'});
  const table=screen.getAllByRole('table')[0];
  const blocked=within(table).getByRole('row',{name:/2025-11-01/});
  expect(within(blocked).getByText('Nhà mạng ngừng mua và bán')).toBeVisible();
  expect(within(blocked).getByText(/Không được bán mới/)).toBeVisible();
  const internal=within(table).getByRole('row',{name:/2025-11-02/});
  expect(within(internal).getByText('Đã ngừng nhập nội bộ')).toBeVisible();
  expect(within(internal).getByText(/Được bán tồn/)).toBeVisible();
  expect(within(table).getByRole('row',{name:/2025-11-03/})).toHaveTextContent('Theo từng sản phẩm');
  view.unmount();
  vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({items:[{target_date:'2025-11-01',supply_status:'active'}],total:1}),{status:200}));
  render(<SellThrough runId="legacy" ctx={{...ctx,warehouseId:'',itemId:''}} />);
  expect(await screen.findByRole('columnheader',{name:'Cung cấp'})).toBeVisible();
  expect(screen.getByText('Đang cung cấp')).toBeVisible();
});
const notice={id:1,supplier_id:1,latest_version:1,latest_action:'stop',latest_known_on:day,as_of_date:day,state:{provider_status:'stopped',sales_allowed:false},scope_items:2,scope_warehouses:2,
  scope_definition:{products:[{sku:'SYN',product_type:'eSIM',destination_countries:['A','B'],warehouse_ids:[1,2]}]},reason:'Synthetic notice',source_description:'Hypothetical',source_ref:null};
const reply=(data:unknown,status=200)=>Promise.resolve({ok:status<300,status,json:async()=>data} as Response);
let posts:{path:string;body:Row}[],reads:string[],stale:boolean,offline:boolean,invalidReason:boolean,capable:boolean;
function fetcher(input:RequestInfo|URL,options?:RequestInit):Promise<Response>{
  const url=new URL(String(input),'http://localhost');if(url.searchParams.has('v'))return reply({error:{code:'invalid_input',message:'Unexpected query field'}},422);reads.push(url.pathname+url.search);
  if(options?.method==='POST'){
    const body=JSON.parse(String(options.body));posts.push({path:url.pathname,body});
    if(invalidReason)return reply({error:{code:'invalid_input',message:'invalid',details:{fields:[{location:['body','reason'],type:'value_error'}]}}},422);
    if(url.pathname.endsWith('/preview'))return reply({preview_fingerprint:fp,scope_items:123,scope_warehouses:2,total:123,items:[{sku:'SYN',warehouse_id:1,destination_country:'A',stock_qty:null,pending_qty:null,after:{internal_status:'active',provider_status:'stopped',replenishment_allowed:false,sales_allowed:false}}],impact:{inventory_complete:false}});
    if(stale)return reply({error:{code:'preview_stale',message:'stale'}},409);
    return reply({notice_id:1},201);
  }
  if(url.pathname.endsWith('/suppliers'))return reply({items:[{id:1,carrier:'Carrier A'},{id:2,carrier:'Carrier B'}],total:2});
  if(url.pathname.endsWith('/warehouses'))return reply({items:[{id:1,city:'First City',destination_country:'A',carrier:'Carrier A'},{id:2,city:'Second City',destination_country:'B',carrier:'Carrier A'},{id:3,city:'Outside City',destination_country:'A',carrier:'Carrier B'}],total:3});
  if(url.pathname.endsWith('/events'))return reply({items:[{id:7,action:'stop',known_on:day,effective_on:day,reason:'Declared',source_description:'Hypothetical'}],total:1});
  if(url.pathname.endsWith('/items'))return reply({items:[],total:0});
  if(url.pathname.endsWith('/provider-product-notices/1'))return reply(notice);
  if(url.pathname.endsWith('/provider-product-notices'))return offline?reply({error:{code:'trade_schema_required',message:'not enabled'}},503):reply({items:[notice],total:51});
  if(url.pathname.endsWith('/products/11'))return reply({id:11,item_id:11,warehouse_id:1,sku:'SYN',city:'First City',carrier:'Carrier A',product_type:'eSIM',trade_schema_ready:true,internal_status:'active',provider_status:'stopped',replenishment_allowed:false,sales_allowed:false,provider_notice_ids:[1],policy:null});
  if(url.pathname.endsWith('/products'))return reply({items:[{trade_schema_ready:capable}],total:1});
  if(url.pathname.endsWith('/scenarios'))return reply({items:[{id:1,name:'Synthetic',version:1}],total:1});
  return reply({items:[],total:0});
}
beforeEach(()=>{posts=[];reads=[];stale=false;offline=false;invalidReason=false;capable=true;history.replaceState(null,'','/');vi.spyOn(globalThis,'fetch').mockImplementation(fetcher);});
afterEach(()=>{cleanup();vi.restoreAllMocks();history.replaceState(null,'','/');});
async function scope(){await screen.findByRole('option',{name:'Carrier A'});fireEvent.change(screen.getByLabelText('Nhà mạng áp dụng'),{target:{value:'1'}});fireEvent.change(screen.getByLabelText('Mã SKU chính xác'),{target:{value:'SYN'}});}
function reasons(){fireEvent.change(screen.getByLabelText('Lý do thay đổi'),{target:{value:'Declared simulation'}});}
async function preview(){fireEvent.click(screen.getByRole('button',{name:'Xem phạm vi và tác động'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Lưu thông báo'})).toBeEnabled());}

it('previews the whole product without market, warehouse or source inputs and saves once',async()=>{
  const saved=vi.fn();render(<ProviderNoticeForm day={day} runs={[]} onClose={()=>{}} onSaved={saved} />);
  expect(screen.getByRole('button',{name:'Lưu thông báo'})).toBeDisabled();await scope();reasons();
  fireEvent.change(screen.getByLabelText('Ngày hiệu lực UTC'),{target:{value:'2025-10-29'}});expect(screen.getByText(/Hệ thống biết sau ngày hiệu lực/)).toBeVisible();
  await preview();expect(screen.getByText(/Toàn phạm vi: 123 mặt hàng \/ 2 kho/)).toBeVisible();expect(screen.getByText(/Chưa có dữ liệu tác động đủ phạm vi/)).toBeVisible();
  expect(posts[0].body).toMatchObject({action:'stop',supplier_id:1,expected_version:0,effective_on:'2025-10-29',scope_definition:{products:[{sku:'SYN',product_type:'eSIM'}]}});
  expect(posts[0].body.scope_definition).toEqual({products:[{sku:'SYN',product_type:'eSIM'}]});
  expect(posts[0].body).not.toHaveProperty('source_description');
  expect(screen.queryByText('Thị trường áp dụng')).toBeNull();expect(screen.queryByText('Kho áp dụng')).toBeNull();
  expect(screen.queryByLabelText('Nguồn khai báo / giả định')).toBeNull();expect(screen.queryByLabelText('Liên kết tham chiếu (tùy chọn)')).toBeNull();
  expect(reads.some(p=>p.startsWith('/api/v1/warehouses'))).toBe(false);
  expect(posts[0].body).not.toHaveProperty('source_ref');fireEvent.click(screen.getByRole('button',{name:'Sau →'}));await waitFor(()=>expect(posts.filter(p=>p.path.endsWith('/preview'))).toHaveLength(2));
  fireEvent.click(screen.getByRole('button',{name:'Lưu thông báo'}));await waitFor(()=>expect(saved).toHaveBeenCalledWith(1));
  expect(posts.filter(p=>!p.path.endsWith('/preview'))).toHaveLength(1);expect(posts.at(-1)!.body.preview_fingerprint).toBe(fp);
});

it('invalidates preview when the reason changes and retains values on stale-save conflict',async()=>{
  render(<ProviderNoticeForm day={day} runs={[]} onClose={()=>{}} onSaved={()=>{}} />);await scope();reasons();await preview();
  fireEvent.change(screen.getByLabelText('Lý do thay đổi'),{target:{value:'Changed reason'}});expect(screen.getByRole('button',{name:'Lưu thông báo'})).toBeDisabled();
  await preview();stale=true;fireEvent.click(screen.getByRole('button',{name:'Lưu thông báo'}));await screen.findByRole('alert');
  expect(screen.getByLabelText('Lý do thay đổi')).toHaveValue('Changed reason');expect(screen.getByRole('button',{name:'Lưu thông báo'})).toBeDisabled();
  fireEvent.click(screen.getByRole('button',{name:'Tải lại dữ liệu'}));await waitFor(()=>expect(screen.getByRole('button',{name:'Xem phạm vi và tác động'})).toBeEnabled());
  expect(posts.filter(p=>!p.path.endsWith('/preview'))).toHaveLength(1);
});

it.each(['cancel_stop','resume_supply'] as const)('keeps %s distinct and sends the follow-up DTO without action or notice id',async action=>{
  const saved=vi.fn();render(<ProviderNoticeForm notice={notice} action={action} day={day} runs={[]} onClose={()=>{}} onSaved={saved} />);
  reasons();await waitFor(()=>expect(screen.getByRole('button',{name:'Xem phạm vi và tác động'})).toBeEnabled());
  expect(screen.getByText(/Áp dụng theo phạm vi thông báo đã lưu/)).toBeVisible();
  if(action==='resume_supply')fireEvent.change(screen.getByLabelText('Ngày hiệu lực UTC'),{target:{value:'2025-11-04'}});
  else expect(screen.getByLabelText('Ngày hiệu lực UTC')).toHaveAttribute('readonly');
  await preview();expect(posts[0].body).toMatchObject({action,notice_id:1,target_event_id:7,expected_version:1});
  fireEvent.click(screen.getByRole('button',{name:'Lưu thông báo'}));await waitFor(()=>expect(saved).toHaveBeenCalledWith(1));
  expect(posts.at(-1)!.path).toMatch(new RegExp(action==='cancel_stop'?'/1/cancel$':'/1/resume$'));
  expect(posts.at(-1)!.body).not.toHaveProperty('action');expect(posts.at(-1)!.body).not.toHaveProperty('notice_id');
  expect(posts.at(-1)!.body).toMatchObject({target_event_id:7,preview_fingerprint:fp,effective_on:action==='resume_supply'?'2025-11-04':day});
});

it('requires an exact product before preview without asking for a source',async()=>{
  render(<ProviderNoticeForm day={day} runs={[]} onClose={()=>{}} onSaved={()=>{}} />);
  await screen.findByRole('option',{name:'Carrier A'});fireEvent.change(screen.getByLabelText('Nhà mạng áp dụng'),{target:{value:'1'}});
  expect(screen.queryByText('Outside City')).toBeNull();expect(screen.getByRole('button',{name:'Xem phạm vi và tác động'})).toBeDisabled();
  await scope();fireEvent.change(screen.getByLabelText('Lý do thay đổi'),{target:{value:'Reason'}});await preview();
  expect(posts).toHaveLength(1);expect(posts[0].body.scope_definition).toEqual({products:[{sku:'SYN',product_type:'eSIM'}]});
});

it('preserves filter pagination, a cleared date and readable schema errors across retry',async()=>{
  history.replaceState(null,'','/?notice_day='+day+'#provider-notices');
  render(<ProviderNotices page="provider-notices" day={day} runs={[]} navigate={()=>{}} />);
  await screen.findByText('Synthetic notice');fireEvent.click(screen.getByRole('button',{name:'Sau →'}));await waitFor(()=>expect(reads.some(p=>p.includes('page=2'))).toBe(true));
  fireEvent.change(screen.getByLabelText('Trạng thái nhà mạng'),{target:{value:'stopped'}});await waitFor(()=>expect(reads.some(p=>p.includes('status=stopped') && p.includes('page=1'))).toBe(true));
  offline=true;fireEvent.change(screen.getByLabelText('Ngày xem thông báo UTC'),{target:{value:''}});await screen.findByRole('alert');expect(location.search).toContain('notice_day=');
  offline=false;fireEvent.click(screen.getByRole('button',{name:'Tải lại danh sách'}));await screen.findByText('Synthetic notice');expect(screen.getByLabelText('Ngày xem thông báo UTC')).toHaveValue('');
  expect(location.search).not.toContain('notice_day=2025');
});

it('prefills a product-scoped provider notice without treating the initial scope as a dirty draft',async()=>{
  const close=vi.fn(),confirm=vi.spyOn(window,'confirm').mockReturnValue(false);
  render(<ProviderNoticeForm initialProduct={{id:11,sku:'SYN',product_type:'eSIM',supplier_id:1,warehouse_id:1,destination_country:'A'}} day={day} runs={[]} onClose={close} onSaved={()=>{}} />);
  await waitFor(()=>expect(screen.getByLabelText('Nhà mạng áp dụng')).toHaveValue('1'));
  expect(screen.getByLabelText('Nhà mạng áp dụng')).toBeDisabled();
  expect(screen.getByLabelText('Mã SKU chính xác')).toHaveValue('SYN');
  expect(screen.getByLabelText('Mã SKU chính xác')).toHaveAttribute('readonly');
  expect(screen.getByLabelText('Loại sản phẩm')).toBeDisabled();expect(screen.queryByRole('checkbox')).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Quay lại lịch cung cấp'}));expect(close).toHaveBeenCalledOnce();expect(confirm).not.toHaveBeenCalled();
});

it('round trips frozen rights/window and provider filters through navigation without exposing the profile picker',()=>{
  const value={...ctx,internalStatus:'stopped',providerStatus:'scheduled_resume',salesAllowed:'false',windowOrigin:day};
  history.replaceState(null,'','?'+contextUrl(value)+'&notice_day=&notice_sku=SYN#provider-notices');expect(readContext()).toEqual(value);
  expect(navigationUrl(value,'provider-notice:1','recommendations')).toContain('notice_sku=SYN');expect(navigationUrl(value,'provider-notice:1','recommendations')).toContain('notice_day=');
});

it('automatically adds the supported trade marker only for inventory runs',async()=>{
  const forecast:Run={id:'forecast',kind:'forecast',status:'complete',as_of_date:day,observation_end:day,source_import_run_id:'source',forecast_run_id:null,scenario_id:null,config_version:'test',assumption_version:'test',target_version:'test',error_code:null,result_summary:{origins:1},period_start:null,period_end:null,created_at:day};
  render(<RunForm scenario={{ id: 1, name: "Base", version: 1 }} runs={[forecast]} onCreated={()=>{}} />);await waitFor(()=>expect(screen.getByRole('button',{name:'Chạy kịch bản'})).toBeEnabled());
  fireEvent.submit(screen.getByRole('button',{name:'Chạy kịch bản'}).closest('form')!);
  await waitFor(()=>expect(posts).toHaveLength(1));expect(posts[0].body.trade_lifecycle_profile).toBe('internal_provider_trade_v2');
  expect(posts[0].body.scenario_supply_profile).toBe('scenario_supply_v1');
  expect(screen.queryByText('internal_provider_trade_v2')).toBeNull();
});


it('focuses the rejected field and preserves the draft after a validation error',async()=>{
  render(<ProviderNoticeForm day={day} runs={[]} onClose={()=>{}} onSaved={()=>{}} />);await scope();reasons();invalidReason=true;
  fireEvent.click(screen.getByRole('button',{name:'Xem phạm vi và tác động'}));await screen.findByRole('alert');
  await waitFor(()=>expect(screen.getByLabelText('Lý do thay đổi')).toHaveFocus());expect(screen.getByLabelText('Lý do thay đổi')).toHaveValue('Declared simulation');
  expect(screen.getByText('Kiểm tra: Lý do thay đổi')).toBeVisible();expect(screen.getByRole('button',{name:'Lưu thông báo'})).toBeDisabled();
});

it('asks before discarding a dirty form and keeps its values when staying',async()=>{
  const close=vi.fn(),confirm=vi.spyOn(window,'confirm').mockReturnValue(false);
  render(<ProviderNoticeForm day={day} runs={[]} onClose={close} onSaved={()=>{}} />);await scope();reasons();
  fireEvent.click(screen.getByRole('button',{name:'Quay lại danh sách thông báo'}));expect(confirm).toHaveBeenCalledTimes(1);expect(close).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Lý do thay đổi')).toHaveValue('Declared simulation');
  const event=new Event('sigma:before-navigate',{cancelable:true});expect(window.dispatchEvent(event)).toBe(false);
  confirm.mockReturnValue(true);fireEvent.click(screen.getByRole('button',{name:'Quay lại danh sách thông báo'}));expect(close).toHaveBeenCalledTimes(1);
});


it('disables provider writes on the application schema without trade support',async()=>{
  capable=false;render(<ProviderNoticeForm day={day} runs={[]} onClose={()=>{}} onSaved={()=>{}} />);
  await screen.findByText(/Không thể lưu thông báo/);expect(screen.getByLabelText('Nhà mạng áp dụng')).toBeDisabled();
  expect(screen.getByRole('button',{name:'Xem phạm vi và tác động'})).toBeDisabled();expect(screen.getByRole('button',{name:'Lưu thông báo'})).toBeDisabled();expect(posts).toHaveLength(0);
});
