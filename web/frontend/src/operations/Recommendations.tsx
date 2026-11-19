import { useState } from "react";
import { useResource } from "../hooks/useResource";
import { State } from "../components/ui/State";
import { Table } from "../components/ui/Table";
import { Pager } from "../components/ui/Pager";
import type { Page, Row } from "../types/api";
import { qty } from "./types";

interface Plan extends Page { origin: string; forecast_origin: string | null; captured_at: string; forecast_run_id: string | null; forecast_options: string[] }
const REASONS: Record<string,string> = {
  current_forecast_missing: "Chưa có dự báo gần ngày hiện tại cho sản phẩm.",
  fixed_policy_missing: "Chưa có chính sách nhập đang hiệu lực. Thiết lập tại Danh mục › Sản phẩm › Chính sách nhập.",
  forecast_horizon_short: "Thời gian nhập và một ngày xét bổ sung vượt kỳ dự báo hiện có. Cần dự báo dài hơn.",
  forecast_incomplete: "Thiếu ngày dự báo hoặc số lượng không hợp lệ.",
  quantity_out_of_range: "Số lượng vượt giới hạn xử lý; cần đối chiếu.",
  supply_restricted: "Có lịch ngừng nhập hoặc ngừng dịch vụ trong kỳ. Cần đối chiếu lịch cung cấp.",
  overdue_receipt_unknown: "Có đơn quá ngày dự kiến nhưng chưa nhận. Xác minh lịch giao trước khi đặt trùng.",
  fixed_lot_policy: "Áp dụng lượng nhập cố định đã cấu hình.",
  fixed_threshold_policy: "Theo ngưỡng cố định: chưa có dự báo, so tồn và hàng về đúng kỳ với ROP tối thiểu.",
};
const DECISIONS: Record<string,string> = { blocked:"Chưa đủ điều kiện", review_overdue:"Kiểm tra đơn trễ", order:"Cần bổ sung", covered:"Chưa cần đặt" };
export function Recommendations() {
  const [page,setPage] = useState(1), [run,setRun] = useState("");
  const result = useResource<Plan>(`/operations/recommendations?page=${page}&page_size=25${run ? `&forecast_run_id=${encodeURIComponent(run)}` : ""}`, true);
  const [detail,setDetail] = useState<Row>();
  return <section className="panel ops-list-panel"><h2>Đề xuất nhập từ sổ kho</h2>
    <p>Tổng hợp mỗi sản phẩm trên tất cả kho; mỗi dự báo chỉ tính một lần. Đây là khuyến nghị để đối chiếu, chưa tạo đơn mua.</p>
    <p className="notice">Giả định: giữ số dư hiện tại đến đầu ngày UTC tiếp theo; chưa tính nhu cầu còn lại trong ngày và thời gian chuyển giữa các kho. Hàng quá ngày về không được coi là đã nhận.</p>
    {/* Keep the panel while another page or forecast loads; only the table shows the skeleton. */}
    <State loading={result.loading && !result.data} error={result.error} />
    {result.data && !result.error && <>
      <label>Nguồn dự báo<select value={run} onChange={event=>{setRun(event.target.value);setPage(1);setDetail(undefined);}}><option value="">Tự chọn lượt gần nhất đủ điều kiện</option>{result.data.forecast_options.map(id=><option key={id} value={id}>{id.slice(0,8)}</option>)}</select></label>
      <p className="caption">Khi chưa có dự báo cho ngày hiện tại, sản phẩm được tính theo ngưỡng cố định: tồn toàn mạng + hàng về trong thời gian nhập ≤ ROP tối thiểu thì đề xuất đặt đúng lượng nhập mỗi lần.</p>
      <p className="caption">Chốt xem: {new Date(result.data.captured_at).toLocaleString("vi-VN")} · Kỳ từ sau {result.data.origin} UTC · Dự báo tại {result.data.forecast_origin ?? "chưa có"}. SS theo bình quân ngày dự báo; ROP theo thời gian nhập + SS và ngưỡng tối thiểu.</p>
      <Table rows={result.data.items} loading={result.loading} stickyFirstColumn columns={[
        {key:"sku",label:"Sản phẩm",render:(value,row)=><span><strong>{String(row.name)}</strong><small className="cell-subtitle">{String(value)} · {String(row.carrier)}</small></span>},{key:"on_hand_qty",label:"Tồn toàn mạng",render:qty},
        {key:"lead_time_days",label:"Thời gian nhập (ngày)"},{key:"rop",label:"Ngưỡng đặt",render:qty},{key:"recommended_qty",label:"Đề xuất nhập",render:qty},
        {key:"basis",label:"Cách tính",render:(value)=><span className={`ops-status ${value==="forecast"?"ordered":""}`}>{value==="forecast"?"Theo dự báo":"Theo ngưỡng cố định"}</span>},
        {key:"decision",label:"Kết luận",render:(value,row)=><span className={value==="order"?"recommend-order":undefined}>{DECISIONS[String(value)]}<small className="cell-subtitle">{REASONS[String(row.reason)]}</small></span>},
        {key:"item_id",label:"Đối chiếu",render:(_,row)=><button disabled={!row.projection} onClick={()=>setDetail(row)}>Xem từng ngày</button>},
      ]} /><Pager page={page} total={result.data.total} pageSize={25} loading={result.loading} onChange={value=>{setPage(value);setDetail(undefined);}} />
      {detail && <section><h3>Dự kiến tồn · {String(detail.sku)}</h3><p>SS: {qty(detail.safety_stock)} · Đang về đúng kỳ: {qty(detail.eligible_pending_qty)} · Quá hạn: {qty(detail.overdue_qty)}.</p>
        {detail.shortage_before_new_eta === true && <p className="notice error">Có nguy cơ thiếu trước khi đơn mới về. Đặt thông thường chưa giải quyết được; cần kiểm tra giao sớm hoặc điều phối kho.</p>}
        <Table rows={detail.projection as Row[]} columns={[{key:"date",label:"Ngày UTC"},{key:"demand",label:"Nhu cầu dự báo"},{key:"receipts_qty",label:"Dự kiến nhận",render:qty},{key:"closing_qty",label:"Tồn cuối dự kiến"},{key:"shortage_qty",label:"Chưa đáp ứng"}]} /></section>}
    </>}
  </section>;
}
