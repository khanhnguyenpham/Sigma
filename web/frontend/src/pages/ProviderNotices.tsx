import { useEffect, useRef, useState } from "react";
import type { Page, Row, Run } from "../types/api";
import { ApiError } from "../services/http";
import { useResource } from "../hooks/useResource";
import { query } from "../utils/url";
import { fmt, text } from "../utils/format";
import { providerLabel } from "../utils/trade";
import { Panel } from "../components/ui/Panel";
import { State } from "../components/ui/State";
import { Table } from "../components/ui/Table";
import { Pager } from "../components/ui/Pager";
import { ProviderNoticeForm } from "../components/products/ProviderNoticeForm";
import { TradeRights } from "../components/products/TradePresentation";

const filterKeys=["day","supplier","sku","type","country","warehouse","status","page"] as const;
function readFilters(day:string){const p=new URLSearchParams(location.search);return Object.fromEntries(filterKeys.map(k=>[k,p.get("notice_"+k) ?? (k==="day"?day:k==="page"?"1":"")])) as Record<typeof filterKeys[number],string>;}
function noticeStatus(row:Row){const state=row.state as Row|null;if(!state)return "Chọn ngày xem trạng thái";if(state.provider_status==="clear"){if(String(row.as_of_date)<String(row.latest_known_on))return "Không có hạn chế đã biết tại ngày xem";return row.latest_action==="cancel_stop"?"Đã hủy thông báo":row.latest_action==="resume_supply"?"Đã cung cấp trở lại":"Không có hạn chế đã biết tại ngày xem";}return providerLabel(state.provider_status);}
function products(row:Row){return ((row.scope_definition as {products?:Row[]})?.products ?? []).map(p=>`${p.sku} · ${p.product_type}`).join("; ");}
export function ProviderNotices({page,day,runs,run,navigate,onItem}: {page:string;day:string;runs:Run[];run?:Run;navigate:(page:string)=>void;onItem?:(row:Row)=>void}) {
  const [filters,setFilters]=useState(()=>readFilters(day)),[revision,setRevision]=useState(0),[eventPage,setEventPage]=useState(1),[itemPage,setItemPage]=useState(1);
  const [follow,setFollow]=useState<"cancel_stop"|"resume_supply">(),[message,setMessage]=useState("");
  const heading=useRef<HTMLHeadingElement>(null),savedMessage=useRef<HTMLParagraphElement>(null);
  useEffect(()=>{if(message)savedMessage.current?.focus();},[message]);
  const listPage=page==="provider-notices",create=page==="provider-notice-new",id=page.startsWith("provider-notice:")?page.split(":")[1]:"";
  const validId=/^[1-9]\d*$/.test(id),selectedDay=filters.day;
  useEffect(()=>{const pop=()=>setFilters(readFilters(day));window.addEventListener("popstate",pop);return()=>window.removeEventListener("popstate",pop);},[day]);
  useEffect(()=>{const params=new URLSearchParams(location.search);filterKeys.forEach(k=>{if(filters[k] || k==="day")params.set("notice_"+k,filters[k]);else params.delete("notice_"+k);});history.replaceState(null,"","?"+params.toString()+location.hash);},[JSON.stringify(filters),page]);
  useEffect(()=>{setFollow(undefined);setMessage("");setEventPage(1);setItemPage(1);heading.current?.focus();},[page]);
  const suppliers=useResource<Page>(listPage?"/suppliers?page_size=100":null),warehouses=useResource<Page>(listPage?"/warehouses?page_size=100":null);
  const list=useResource<Page>(listPage?`/provider-product-notices?${query({as_of_date:selectedDay,supplier_id:filters.supplier,sku:filters.sku,product_type:filters.type,destination_country:filters.country,warehouse_id:filters.warehouse,status:selectedDay?filters.status:undefined,page:Number(filters.page)||1,page_size:50})}`:null,false,revision);
  const detail=useResource<Row>(validId?`/provider-product-notices/${id}?${query({as_of_date:selectedDay})}`:null,true,revision);
  const row=String(detail.data?.id)===id?detail.data:undefined;
  const events=useResource<Page>(row?`/provider-product-notices/${id}/events?${query({page:eventPage,page_size:50})}`:null,false,revision);
  const items=useResource<Page>(row?`/provider-product-notices/${id}/items?${query({as_of_date:selectedDay,page:itemPage,page_size:50})}`:null,false,revision);
  function filter(key:typeof filterKeys[number],value:string){setFilters(f=>({...f,[key]:value,page:key==="page"?value:"1"}));}
  const back=()=>navigate("provider-notices");
  if(create)return <ProviderNoticeForm day={selectedDay} runs={runs} run={run} onClose={back} onSaved={key=>navigate(`provider-notice:${key}`)} />;
  return <>
    <div className="page-heading provider-heading"><div><h1 ref={heading} tabIndex={-1}>{listPage?"Thông báo ngừng sản phẩm":"Chi tiết thông báo ngừng sản phẩm"}</h1><p>Cấu hình mới nhất do người dùng khai báo · Giả định mô phỏng. Kế hoạch đã chốt giữ nguyên.</p></div>
      {listPage?<button className="primary" disabled={list.loading || list.error instanceof ApiError && list.error.code==="trade_schema_required"} onClick={()=>navigate("provider-notice-new")}>Tạo thông báo</button>:<button className="secondary" onClick={back}>← Danh sách thông báo</button>}</div>
    {message && <p className="notice success" role="status" ref={savedMessage} tabIndex={-1}>{message}</p>}
    <label className="supply-date">Ngày xem thông báo UTC<input type="date" value={selectedDay} onChange={e=>filter("day",e.target.value)} /></label>
    {listPage?<Panel title="Các thông báo" note="Mỗi thông báo là một dòng cho toàn bộ phạm vi, không lặp theo kho.">
      <div className="provider-filters"><label>Nhà mạng<select value={filters.supplier} onChange={e=>filter("supplier",e.target.value)}><option value="">Tất cả nhà mạng</option>{suppliers.data?.items.map(s=><option key={String(s.id)} value={String(s.id)}>{String(s.carrier)}</option>)}</select></label>
        <label>SKU chính xác<input value={filters.sku} maxLength={200} onChange={e=>filter("sku",e.target.value)} /></label>
        <label>Loại SIM/eSIM<select value={filters.type} onChange={e=>filter("type",e.target.value)}><option value="">Tất cả loại</option><option>eSIM</option><option>physical_SIM</option></select></label>
        <label>Thị trường<select value={filters.country} onChange={e=>filter("country",e.target.value)}><option value="">Tất cả thị trường</option>{[...new Set(warehouses.data?.items.map(w=>String(w.destination_country)))].sort().map(c=><option key={c}>{c}</option>)}</select></label>
        <label>Kho áp dụng<select value={filters.warehouse} onChange={e=>filter("warehouse",e.target.value)}><option value="">Tất cả kho</option>{warehouses.data?.items.map(w=><option key={String(w.id)} value={String(w.id)}>{String(w.city)} · {String(w.destination_country)}</option>)}</select></label>
        <label>Trạng thái nhà mạng<select value={filters.status} disabled={!selectedDay} onChange={e=>filter("status",e.target.value)}><option value="">Tất cả trạng thái</option><option value="clear">Đã hủy / đã cung cấp lại / chưa có hạn chế</option><option value="scheduled_stop">Chưa hiệu lực</option><option value="stopped">Đã hiệu lực</option><option value="scheduled_resume">Chờ cung cấp trở lại</option></select></label>
      </div><button className="text-button" onClick={()=>setFilters({...readFilters(selectedDay),supplier:"",sku:"",type:"",country:"",warehouse:"",status:"",page:"1"})}>Xóa bộ lọc thông báo</button>
      <State loading={list.loading} error={list.error ?? suppliers.error ?? warehouses.error} />
      {!list.loading && !list.error && list.data?.total===0 && <p className="notice">{Object.entries(filters).some(([k,v])=>!["day","page"].includes(k) && v)?"Không có kết quả theo bộ lọc.":"Chưa có thông báo. Bạn có thể tạo thông báo mới."}</p>}
      {list.error && <button onClick={()=>setRevision(v=>v+1)}>Tải lại danh sách</button>}
      {list.data && <><Table rows={list.data.items} onRow={r=>navigate(`provider-notice:${r.id}`)} columns={[
        {key:"scope_definition",label:"Sản phẩm / phạm vi",render:(_,r)=>products(r)},{key:"scope_items",label:"Mặt hàng"},{key:"scope_warehouses",label:"Kho"},
        {key:"latest_known_on",label:"Ngày ghi nhận mới nhất"},{key:"stop_on",label:"Hiệu lực ngừng",render:(_,r)=>text((r.state as Row|null)?.stop_on)},{key:"state",label:"Trạng thái",render:(_,r)=>noticeStatus(r)},{key:"reason",label:"Lý do"},
      ]} /><Pager page={Number(filters.page)||1} total={list.data.total} onChange={p=>filter("page",String(p))} /></>}
    </Panel>:<>
      <State loading={detail.loading} error={detail.error ?? (!validId?new Error("Không tìm thấy thông báo trong liên kết."):undefined)} />
      {detail.error && <button onClick={()=>setRevision(v=>v+1)}>Tải lại thông báo</button>}
      {row && <><Panel title={products(row)} note={`Toàn phạm vi: ${fmt(row.scope_items)} mặt hàng / ${fmt(row.scope_warehouses)} kho · Giả định mô phỏng`}>
        <p><strong>{noticeStatus(row)}</strong></p><p className="caption">Hiệu lực ngừng: {text((row.state as Row|null)?.stop_on)} · Cung cấp lại từ: {text((row.state as Row|null)?.resume_on)}</p><dl className="drawer-fields"><div><dt>Lý do</dt><dd>{text(row.reason)}</dd></div><div><dt>Nguồn khai báo</dt><dd>{text(row.source_description)}</dd></div></dl>
        {typeof row.source_ref==="string" && /^https?:\/\//i.test(row.source_ref) && <p><a href={row.source_ref} target="_blank" rel="noreferrer">Xem liên kết tham chiếu</a></p>}
        {selectedDay && selectedDay<String(row.latest_known_on) && <p className="notice">Ngày xem trước thay đổi mới nhất. Lịch sử vẫn được giữ; chọn ngày ghi nhận phù hợp trước khi thao tác.</p>}
        <div className="form-actions">{selectedDay && selectedDay>=String(row.latest_known_on) && row.latest_action==="stop" && Number(row.latest_version)===1 && <>
          {(row.state as Row|null)?.provider_status==="scheduled_stop" && <button disabled={detail.loading} onClick={()=>setFollow("cancel_stop")}>Hủy thông báo chưa hiệu lực</button>}
          {(row.state as Row|null)?.sales_allowed===false && <button disabled={detail.loading} onClick={()=>setFollow("resume_supply")}>Ghi nhận cung cấp trở lại</button>}
        </>}</div><p className="caption">Gỡ thông báo này không gỡ ngừng nhập nội bộ hoặc thông báo nhà mạng khác.</p>
      </Panel>
      <Panel title="Lịch sử thông báo"><State loading={events.loading} error={events.error} /><Table rows={events.data?.items ?? []} columns={[{key:"known_on",label:"Ngày biết"},{key:"effective_on",label:"Hiệu lực"},{key:"action",label:"Thao tác",render:v=>({stop:"Ngừng sản phẩm",cancel_stop:"Hủy thông báo",resume_supply:"Cung cấp trở lại"}[String(v)] ?? text(v))},{key:"reason",label:"Lý do"},{key:"source_description",label:"Nguồn giả định"}]} /><Pager page={eventPage} total={events.data?.total ?? 0} onChange={setEventPage} /></Panel>
      <Panel title="Sản phẩm và kho trong phạm vi" note="Chọn sản phẩm để mở chi tiết. Quyền theo cấu hình tại ngày xem. Số tồn và lô cần kế hoạch/ngày cụ thể trong phần xem tác động."><State loading={items.loading} error={items.error} /><Table rows={items.data?.items ?? []} onRow={onItem} columns={[{key:"sku",label:"Sản phẩm"},{key:"product_type",label:"Loại"},{key:"city",label:"Kho"},{key:"destination_country",label:"Thị trường"},{key:"rights",label:"Quyền tại ngày xem",render:(_,r)=><TradeRights row={r} />}]} /><Pager page={itemPage} total={items.data?.total ?? 0} onChange={setItemPage} /></Panel>
      {follow && <ProviderNoticeForm notice={row} action={follow} day={selectedDay} runs={runs} run={run} onClose={()=>setFollow(undefined)} onReload={()=>setRevision(v=>v+1)} onSaved={()=>{setFollow(undefined);setRevision(v=>v+1);setMessage("Đã lưu thông báo. Tạo kế hoạch mới để tính tác động; kế hoạch đang xem giữ nguyên.");}} />}
      </>}
    </>}
  </>;
}
