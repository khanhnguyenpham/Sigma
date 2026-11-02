import type { Row } from "../../types/api";
import { ApiError } from "../../services/http";
import { errorLabel } from "../../utils/labels";
import { fmt, text } from "../../utils/format";
import { internalLabel, providerLabel, capLabel, isTradeRow } from "../../utils/trade";
import { Table } from "../ui/Table";
import { Pager } from "../ui/Pager";

const fieldLabels:Record<string,string>={reason:"Lý do thay đổi",source_description:"Nguồn khai báo / giả định",source_ref:"Liên kết tham chiếu",known_on:"Ngày ghi nhận",effective_on:"Ngày hiệu lực",sku:"Mã SKU",product_type:"Loại sản phẩm",supplier_id:"Nhà mạng",destination_countries:"Thị trường",warehouse_ids:"Kho áp dụng"};

export function TradeRights({row}: {row:Row}) {
  const reasons=Array.isArray(row.provider_reasons)?row.provider_reasons:(row.provider_blockers as Row[]|undefined)?.map(b=>b.reason) ?? [];
  return <div className="trade-rights"><p><strong>Nhập nội bộ:</strong> {internalLabel(row.internal_status)}{row.internal_reason ? ` · ${text(row.internal_reason)}` : ""}</p>
    <p><strong>Nhà mạng:</strong> {providerLabel(row.provider_status)}{reasons.length ? ` · ${reasons.join("; ")}` : ""}</p>
    <p><strong>Quyền nhập:</strong> {row.replenishment_allowed == null ? "Chưa có dữ liệu" : row.replenishment_allowed ? "Được nhập" : "Không được nhập"} · <strong>Quyền bán:</strong> {row.sales_allowed == null ? "Chưa có dữ liệu" : row.sales_allowed ? "Được bán tồn" : "Không được bán mới"}</p>
    {row.needs_supplier_action === true && <p className="notice">Cần xử lý với nhà cung cấp. Lô đã đặt và tổng tồn vẫn được giữ.</p>}</div>;
}
export function TradeQuantities({row}: {row:Row}) {
  if (!isTradeRow(row)) return <p className="caption">Quyền bán và tồn bị chặn: không có trong kế hoạch này.</p>;
  return <><dl className="drawer-fields"><div><dt>Tổng tồn</dt><dd>{row.total_qty == null ? "Chưa có dữ liệu" : fmt(row.total_qty)}</dd></div><div><dt>Tồn được phép bán</dt><dd>{row.sellable_qty == null ? "Chưa có dữ liệu" : fmt(row.sellable_qty)}</dd></div><div><dt>Tồn bị chặn</dt><dd>{row.blocked_qty == null ? "Chưa có dữ liệu" : fmt(row.blocked_qty)}</dd></div>
    <div><dt>Q trước giới hạn</dt><dd>{row.q_policy == null ? "Chưa có dữ liệu" : fmt(row.q_policy)}</dd></div><div><dt>Q sau giới hạn</dt><dd>{row.q_final == null ? "Chưa có dữ liệu" : fmt(row.q_final)}</dd></div></dl>
    {row.cap_reason != null && <p className="notice">{capLabel(row.cap_reason)}</p>}</>;
}
export function TradeTotals({summary}: {summary?:Row}) {
  if (!summary || summary.provider_blocked_items == null) return null;
  return <div className="trade-totals" aria-label="Hạn chế trong kế hoạch"><span>Ngừng nhập nội bộ <strong>{fmt(summary.internal_stopped_items)}</strong></span><span>Nhà mạng chặn bán <strong>{fmt(summary.provider_blocked_items)}</strong></span><span>Mặt hàng bị ảnh hưởng <strong>{fmt(summary.affected_items)}</strong></span><span>Tồn được bán <strong>{fmt(summary.sellable_units)}</strong></span><span>Tồn bị chặn <strong>{fmt(summary.blocked_units)}</strong></span></div>;
}
export function TradeWriteState({state}: {state:{error?:Error; conflict:boolean; uncertain:boolean; saved?:Row; busy:boolean; reload:()=>Promise<void>}}) {
  return <>{state.saved && <p className="notice success" role="status">Đã lưu. {state.error ? "Chưa tải lại được dữ liệu; chỉ cần tải lại, không gửi lại thay đổi." : "Đang tải lại dữ liệu đã lưu…"}</p>}
    {state.uncertain && !state.saved && <p className="notice">Chưa xác nhận được kết quả lưu. Kiểm tra lịch sử trước khi thao tác lại.</p>}
    {state.error && <div className="notice error" role="alert">{errorLabel(state.error)}
      {state.error instanceof ApiError && state.error.details?.fields?.map((f,i)=><p key={i}>Kiểm tra: {fieldLabels[String(f.location.at(-1))] ?? "Phạm vi và thông tin khai báo"}</p>)}
      <button type="button" disabled={state.busy} onClick={()=>void state.reload()}>Tải lại dữ liệu</button></div>}</>;
}
export function TradePreview({data,page,onPage}: {data:Row;page:number;onPage:(page:number)=>void}) {
  const impact=data.impact as Row | undefined, rows=data.items as Row[] | undefined;
  return <section className="trade-preview" aria-label="Phạm vi và tác động"><h3>Phạm vi và tác động</h3>
    {data.scope_items != null && <p><strong>Toàn phạm vi: {fmt(data.scope_items)} mặt hàng / {fmt(data.scope_warehouses)} kho.</strong> Trang {page} chỉ là một phần danh sách.</p>}
    <p>{impact?.inventory_complete ? `Kế hoạch đã chốt tại ${text(impact.as_of_date)} · tồn tổng ${fmt(impact.stock_qty)}, được bán ${fmt(impact.sellable_qty)}, bị chặn ${fmt(impact.blocked_qty)}, đang về ${fmt(impact.pending_qty)}.` : "Chưa có dữ liệu tác động đủ phạm vi/ngày. Bạn vẫn có thể lưu cấu hình hợp lệ."}</p>
    {impact?.rights_quantities_available === false && impact?.inventory_complete === true && <p>Quyền bán và lượng bị chặn chưa có trong kế hoạch đang chọn.</p>}
    <p>Lô đã đặt vẫn được nhận đúng ETA. Q theo cấu hình mới chỉ được tính khi tạo kế hoạch; số liệu kế hoạch đang xem giữ nguyên.</p>
    {data.after != null && <TradeRights row={data.after as Row} />}
    {rows && <><Table rows={rows} columns={[{key:"sku",label:"Sản phẩm"},{key:"destination_country",label:"Thị trường"},{key:"warehouse_id",label:"Kho"},{key:"stock_qty",label:"Tồn theo kế hoạch"},{key:"pending_qty",label:"Đang về"},{key:"after",label:"Quyền sau thay đổi",render:v=><TradeRights row={v as Row} />}]} /><Pager page={page} total={Number(data.total ?? 0)} onChange={onPage} /></>}
  </section>;
}
export function focusTradeError(form:HTMLFormElement|null,error:unknown) {
  if (!(error instanceof ApiError)) return;
  const location=error.details?.fields?.[0]?.location ?? [],field=String(location.at(-1) ?? "");
  const candidates=Array.from(form?.elements ?? []).filter(e=>e instanceof HTMLElement && e.getAttribute("name")===field);
  const index=location.indexOf("products"),product=index<0?0:Number(location[index+1])||0;
  const element=candidates[product] as HTMLElement | undefined;
  element?.scrollIntoView?.({block:"nearest"});
  element?.focus();
}
