import { useEffect, useRef, useState } from "react";
import type { Page, Row, Run } from "../../types/api";
import { useResource } from "../../hooks/useResource";
import { useDialogFocus } from "../../hooks/useDialogFocus";
import { useTradeWrite } from "../../hooks/useTradeWrite";
import { useTradeNavigation } from "../../hooks/useTradeNavigation";
import { api } from "../../services/http";
import { query } from "../../utils/url";
import { warehouseName } from "../../utils/warehouse";
import { Table } from "../ui/Table";
import { Pager } from "../ui/Pager";
import { State } from "../ui/State";
import { TradePreview, TradeWriteState, focusTradeError } from "./TradePresentation";

interface History extends Page { supply_version:number;state:Row|null }
export function ProductSupplyForm({product,day,onDate,onSaved,onClose=()=>{},run,action="stop"}: {
  product:Row;day:string;onDate:(day:string)=>void;onSaved:()=>void;onClose?:()=>void;run?:Run;action?:"stop"|"cancel_stop"|"resume";stock?:Row;
}) {
  const [known,setKnown]=useState(day),[effective,setEffective]=useState(day),[reason,setReason]=useState("");
  const [revision,setRevision]=useState(0),[page,setPage]=useState(1);
  const form=useRef<HTMLFormElement>(null),ready=product.trade_schema_ready===true;
  const path=`/products/${product.id}/supply-changes?${query({as_of_date:known,page,page_size:50})}`;
  const history=useResource<History>(ready?path:null,false,revision),state=history.data?.state;
  const compatible=state?.supply_status===(action==="stop"?"active":action==="cancel_stop"?"scheduled_stop":"stopped");
  const stale=state && state.version!==history.data?.supply_version;
  const impact=run?.status==="complete" && ["stock_projection","policy_replay","alert_replay"].includes(run.kind) && known?{impact_run_id:run.id,impact_as_of_date:known}:{};
  const write=useTradeWrite({draft:{action,known_on:known,effective_on:action==="stop"?effective:known,reason:reason.trim(),expected_version:history.data?.supply_version ?? 0,target_change_id:action==="stop"?null:state?.stop_change_id,...impact},
    previewPath:`/products/${product.id}/internal-stop-preview`,savePath:`/products/${product.id}/supply-changes`,reload:async()=>{await api(path);setRevision(v=>v+1);},onSaved:()=>{navigation.finish();onSaved();}});
  const initialDay=useRef(day),navigation=useTradeNavigation(!write.saved && (!!reason || known!==initialDay.current || effective!==initialDay.current),write.saving,onClose,true);
  useDialogFocus(true,navigation.close);
  useEffect(()=>focusTradeError(form.current,write.error),[write.error]);
  const title=action==="stop"?"Ngừng nhập nội bộ":action==="cancel_stop"?"Hủy lịch ngừng nhập":"Mở nhập lại nội bộ";
  function preview(){form.current?.querySelector<HTMLTextAreaElement>('[name="reason"]')?.setCustomValidity(reason.trim()?"":"Hãy nhập lý do thay đổi.");if(!form.current?.reportValidity())return;void write.showPreview();}
  const disabled=!ready || !known || !state || !!stale || !compatible || history.loading || !!history.error || !!write.saved || write.uncertain;
  return <div className="modal-shade"><section className="modal trade-modal" role="dialog" aria-modal="true" aria-labelledby="internal-title" aria-describedby="internal-description">
    <button className="close" aria-label="Đóng ngừng nhập nội bộ" disabled={write.saving} onClick={navigation.close}>×</button><h2 id="internal-title">{title}</h2>
    <p>{String(product.sku)} · {String(product.product_type)} · {warehouseName(product)} · {String(product.carrier)}</p>
    <p id="internal-description" className="notice subtle">Chỉ thay đổi quyền nhập tại kho này. Vẫn bán tồn được phép bán và nhận lô đã đặt; hạn chế nhà mạng còn áp dụng.</p>
    {!ready && <p className="notice">Chức năng mới chưa được bật cho dữ liệu này. Lịch sử và kế hoạch cũ được giữ nguyên.</p>}
    <State loading={history.loading} error={history.error} />
    {stale && <p className="notice">Ngày ghi nhận đang trước thay đổi mới nhất. Chọn ngày phù hợp để thao tác.</p>}
    {state && !compatible && !write.saved && <p className="notice">Trạng thái đã thay đổi hoặc không phù hợp hành động này. Đóng và kiểm tra lịch sử trước khi chọn thao tác.</p>}
    <form ref={form} aria-label={title} onSubmit={e=>{e.preventDefault();if(!disabled)void write.save();}}><fieldset disabled={write.busy || !!write.saved || write.uncertain}>
      <div className="form-grid"><label>Ngày ghi nhận UTC<input name="known_on" type="date" required value={known} onChange={e=>{setKnown(e.target.value);onDate(e.target.value);setPage(1);}} /></label>
        <label>Ngày hiệu lực UTC<input name="effective_on" type="date" required min={action==="stop"?known:undefined} readOnly={action!=="stop"} value={action==="stop"?effective:known} onChange={e=>setEffective(e.target.value)} /></label></div>
      <label>Lý do thay đổi<textarea name="reason" required maxLength={1000} value={reason} onChange={e=>{e.target.setCustomValidity("");setReason(e.target.value);}} /></label>
      <div className="form-actions"><button type="button" disabled={disabled || write.conflict} onClick={preview}>{write.previewing?"Đang xem tác động…":"Xem tác động"}</button><button className="primary" disabled={disabled || write.conflict || !write.preview}>{write.saving?"Đang lưu…":`Lưu ${title.toLowerCase()}`}</button></div>
    </fieldset></form><TradeWriteState state={write} />
    {write.preview && <TradePreview data={write.preview} page={1} onPage={()=>{}} />}
    {history.error && <button onClick={()=>setRevision(v=>v+1)}>Tải lại lịch sử</button>}
    <details className="advanced-section"><summary>Lịch sử ngừng nhập nội bộ</summary><Table rows={history.data?.items ?? []} columns={[{key:"known_on",label:"Ngày ghi nhận"},{key:"effective_on",label:"Hiệu lực"},{key:"action",label:"Thao tác",render:v=>({stop:"Ngừng nhập",cancel_stop:"Hủy lịch",resume:"Mở nhập lại"}[String(v)] ?? String(v))},{key:"reason",label:"Lý do"}]} /><Pager page={page} total={history.data?.total ?? 0} onChange={setPage} /></details>
  </section></div>;
}
