import { useEffect, useRef, useState } from "react";
import type { Page, Row, Run } from "../../types/api";
import { useResource } from "../../hooks/useResource";
import { useTradeWrite } from "../../hooks/useTradeWrite";
import { useTradeNavigation } from "../../hooks/useTradeNavigation";
import { useDialogFocus } from "../../hooks/useDialogFocus";
import { api } from "../../services/http";
import { query } from "../../utils/url";
import { State } from "../ui/State";
import { TradePreview, TradeWriteState, focusTradeError } from "./TradePresentation";

interface Scope {sku:string;product_type:string}
const emptyScope=():Scope=>({sku:"",product_type:"eSIM"});
export function ProviderNoticeForm({notice,initialProduct,action="stop",day,runs,run,onSaved,onClose,onReload}: {
  notice?:Row;initialProduct?:Row;action?:"stop"|"cancel_stop"|"resume_supply";day:string;runs:Run[];run?:Run;onSaved:(id:number)=>void;onClose:()=>void;onReload?:()=>void;
}) {
  const follow=action!=="stop";
  const initialSupplier=String(initialProduct?.supplier_id ?? "");
  const initialScope=useRef<Scope[]>(initialProduct?[{sku:String(initialProduct.sku),product_type:String(initialProduct.product_type)}]:[emptyScope()]);
  const [supplier,setSupplier]=useState(initialSupplier),[products,setProducts]=useState<Scope[]>(initialScope.current);
  const [known,setKnown]=useState(day),[effective,setEffective]=useState(day),[reason,setReason]=useState("");
  const plans=runs.filter(r=>r.status==="complete" && ["stock_projection","policy_replay","alert_replay"].includes(r.kind));
  const [impactRun,setImpactRun]=useState(plans.some(r=>r.id===run?.id)?run!.id:""),[impactDay,setImpactDay]=useState(day);
  const suppliers=useResource<Page>(!follow?"/suppliers?page_size=100":null);
  const capability=useResource<Page>("/products?page_size=1"),ready=capability.data?.items[0]?.trade_schema_ready===true;
  const form=useRef<HTMLFormElement>(null),heading=useRef<HTMLHeadingElement>(null);
  useEffect(()=>{if(!follow)heading.current?.focus();},[follow]);
  const events=useResource<Page>(follow?`/provider-product-notices/${notice!.id}/events?page_size=50`:null),stop=events.data?.items.find(e=>e.action==="stop");
  const effectiveOn=action==="cancel_stop"?known:effective;
  const draft:Row={action,known_on:known,effective_on:effectiveOn,reason:reason.trim(),expected_version:follow?notice?.latest_version ?? 0:0,
    ...(follow?{notice_id:notice!.id,target_event_id:stop?.id}:{supplier_id:Number(supplier),scope_definition:{products:products.map(p=>({...p,sku:p.sku.trim()}))}}),...(impactRun && impactDay?{impact_run_id:impactRun,impact_as_of_date:impactDay}:{})};
  const write=useTradeWrite({draft,previewPath:"/provider-product-notices/preview",savePath:follow?`/provider-product-notices/${notice!.id}/${action==="cancel_stop"?"cancel":"resume"}`:"/provider-product-notices",
    saveDraft:body=>follow?Object.fromEntries(Object.entries(body).filter(([k])=>k!=="action" && k!=="notice_id")):body,
    reload:async saved=>{const id=saved?.notice_id ?? notice?.id;await api(id?`/provider-product-notices/${id}?${query({as_of_date:known})}`:"/provider-product-notices?page_size=50");onReload?.();},onSaved:saved=>{navigation.finish();onSaved(Number(saved.notice_id ?? notice?.id));}});
  const initialDay=useRef(day),navigation=useTradeNavigation(!write.saved && (supplier!==initialSupplier || JSON.stringify(products)!==JSON.stringify(initialScope.current) || !!reason || known!==initialDay.current || effective!==initialDay.current),write.saving,onClose,follow);
  useDialogFocus(follow,navigation.close);
  useEffect(()=>focusTradeError(form.current,write.error),[write.error]);
  function changeScope(index:number,patch:Partial<Scope>){setProducts(rows=>rows.map((r,i)=>i===index?{...r,...patch}:r));}
  function preview(){form.current?.querySelector<HTMLTextAreaElement>('[name="reason"]')?.setCustomValidity(reason.trim()?"":"Hãy nhập lý do thay đổi.");if(!form.current?.reportValidity())return;void write.showPreview();}
  const invalidScope=!follow && (!supplier || products.some(p=>!p.sku.trim()));
  const invalidFollow=follow && (!stop || events.loading || !!events.error || notice?.latest_action!=="stop" || Number(notice?.latest_version)!==1 || !known || known<String(notice?.latest_known_on));
  const disabled=!ready || capability.loading || !!capability.error || write.busy || !!write.saved || write.uncertain || invalidScope || invalidFollow;
  const title=action==="stop"?(initialProduct?"Đặt lịch ngừng cung cấp":"Tạo thông báo ngừng sản phẩm"):action==="cancel_stop"?"Hủy thông báo chưa hiệu lực":"Ghi nhận cung cấp trở lại";
  const content=<>
    {follow?<h2 id="provider-form-title">{title}</h2>:<h1 ref={heading} tabIndex={-1}>{title}</h1>}
    <p id="provider-description" className="notice subtle">{follow?"Áp dụng theo phạm vi thông báo đã lưu.":"Áp dụng cho sản phẩm cùng mã SKU và loại sản phẩm của nhà mạng này tại tất cả thị trường và kho."} Ngừng nhập và bán mới; các lô đã đặt vẫn được giữ.</p>
    <State loading={capability.loading || suppliers.loading || events.loading} error={capability.error ?? suppliers.error ?? events.error} />
    {!capability.loading && !capability.error && !ready && <p className="notice">Chức năng mới chưa được bật cho dữ liệu này. Không thể lưu thông báo.</p>}
    {invalidFollow && !events.loading && <p className="notice">Ngày ghi nhận hoặc trạng thái không còn phù hợp. Tải lại và kiểm tra lịch sử; hành động không được tự đổi nghĩa.</p>}
    <form ref={form} aria-label={title} onSubmit={e=>{e.preventDefault();if(!disabled)void write.save();}}><fieldset disabled={!ready || write.busy || !!write.saved || write.uncertain}>
      {!follow && <><label>Nhà mạng áp dụng<select name="supplier_id" required disabled={!!initialProduct} value={supplier} onChange={e=>{setSupplier(e.target.value);setProducts([emptyScope()]);}}><option value="">Chọn nhà mạng</option>{suppliers.data?.items.map(s=><option key={String(s.id)} value={String(s.id)}>{String(s.carrier)}</option>)}</select></label>
        {products.map((p,index)=><section className="scope-product" key={index} aria-label={`Sản phẩm trong phạm vi ${index+1}`}><div className="form-grid">
          <label>Mã SKU chính xác<input name="sku" required readOnly={!!initialProduct} maxLength={200} value={p.sku} onChange={e=>changeScope(index,{sku:e.target.value.trimStart()})} /></label><label>Loại sản phẩm<select name="product_type" disabled={!!initialProduct} value={p.product_type} onChange={e=>changeScope(index,{product_type:e.target.value})}><option>eSIM</option><option>physical_SIM</option></select></label></div>
          {products.length>1 && <button type="button" onClick={()=>setProducts(rows=>rows.filter((_,i)=>i!==index))}>Bỏ sản phẩm khỏi phạm vi</button>}
        </section>)}{!initialProduct&&<button type="button" onClick={()=>setProducts(rows=>[...rows,emptyScope()])}>Thêm sản phẩm vào phạm vi</button>}</>}
      <div className="form-grid"><label>Ngày biết thông báo UTC<input name="known_on" type="date" required value={known} onChange={e=>setKnown(e.target.value)} /></label><label>Ngày hiệu lực UTC<input name="effective_on" type="date" required readOnly={action==="cancel_stop"} min={action==="resume_supply"?known:undefined} value={effectiveOn} onChange={e=>setEffective(e.target.value)} /></label></div>
      {action==="stop" && known && effective && effective<known && <p className="notice">Hệ thống biết sau ngày hiệu lực. Quyết định trước ngày biết giữ nguyên, không hồi tố.</p>}
      <label>Lý do thay đổi<textarea name="reason" required maxLength={1000} value={reason} onChange={e=>{e.target.setCustomValidity("");setReason(e.target.value);}} /></label>
      <div className="form-grid"><label>Kế hoạch xem tác động<select value={impactRun} onChange={e=>setImpactRun(e.target.value)}><option value="">Chưa chọn kế hoạch</option>{plans.map(p=><option key={p.id} value={p.id}>{p.as_of_date} · {p.id.slice(0,8)}</option>)}</select></label><label>Ngày số liệu tác động UTC<input type="date" value={impactDay} disabled={!impactRun} required={!!impactRun} onChange={e=>setImpactDay(e.target.value)} /></label></div>
      <div className="form-actions"><button type="button" disabled={disabled || write.conflict} onClick={preview}>{write.previewing?"Đang xem phạm vi…":"Xem phạm vi và tác động"}</button><button className="primary" disabled={disabled || write.conflict || !write.preview}>{write.saving?"Đang lưu…":"Lưu thông báo"}</button></div>
    </fieldset></form><TradeWriteState state={write} />
    {write.preview && <TradePreview data={write.preview} page={write.page} onPage={p=>void write.showPreview(p)} />}
    <button className="secondary" disabled={write.saving} onClick={navigation.close}>{follow?"Đóng":initialProduct?"Quay lại lịch cung cấp":"Quay lại danh sách thông báo"}</button>
  </>;
  return follow?<div className="modal-shade"><section className="modal trade-modal" role="dialog" aria-modal="true" aria-labelledby="provider-form-title" aria-describedby="provider-description">{content}</section></div>:<section className="provider-editor">{content}</section>;
}
