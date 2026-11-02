import { useEffect, useRef, useState } from "react";
import type { Page, Row } from "../../types/api";
import { useResource } from "../../hooks/useResource";
import { api, ApiError } from "../../services/http";
import { query } from "../../utils/url";
import { addSupplyDays } from "../../utils/supply";
import { errorLabel } from "../../utils/labels";
import { text } from "../../utils/format";
import { warehouseName } from "../../utils/warehouse";
import { Panel } from "../ui/Panel";
import { Table } from "../ui/Table";
import { Pager } from "../ui/Pager";
import { State } from "../ui/State";
import { badge } from "../ui/Badge";

interface History extends Page { supply_version: number; state: Row | null }
export function ProductSupplyForm({ product, day, onDate, onSaved, stock }: {
  product: Row; day: string; onDate: (day: string) => void; onSaved: () => void; stock?: Row;
}) {
  const [revision, setRevision] = useState(0), [page, setPage] = useState(1);
  const [stopOn, setStopOn] = useState(addSupplyDays(day)), [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false), [error, setError] = useState<Error>(), [message, setMessage] = useState("");
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const sending = useRef(false), notice = useRef<HTMLDivElement>(null);
  const ready = product.supply_schema_ready === true;
  const history = useResource<History>(ready ? `/products/${product.id}/supply-changes?${query({ as_of_date: day, page, page_size: 50, v: revision })}` : null);
  const state = history.data?.state;
  const action = state?.supply_status === "scheduled_stop" ? "cancel_stop" : state?.supply_status === "stopped" ? "resume" : "stop";
  const title = action === "stop" ? "Lên lịch ngừng nhập" : action === "cancel_stop" ? "Hủy lịch ngừng nhập" : "Mở nhập lại";
  const stale = state && state.version !== history.data?.supply_version;
  const conflict = error instanceof ApiError && ["version_conflict", "supply_conflict"].includes(error.code);
  useEffect(() => { if (message) notice.current?.focus(); }, [message]);
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending.current || !day || !state || stale || conflict || !event.currentTarget.reportValidity()) return;
    if (!reason.trim()) { setError(new Error("Hãy nhập lý do thay đổi.")); return; }
    const effective = action === "stop" ? stopOn : day;
    if (action === "stop" && (!addSupplyDays(day) || effective < addSupplyDays(day))) {
      setError(new Error("Ngày ngừng nhập phải sau ngày thông báo ít nhất 7 ngày.")); return;
    }
    sending.current = true; setBusy(true); setError(undefined); setMessage("");
    try {
      await api(`/products/${product.id}/supply-changes`, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, known_on: day, effective_on: effective, reason: reason.trim(),
          expected_version: history.data!.supply_version, target_change_id: action === "stop" ? null : state.stop_change_id }) });
      if (!mounted.current) return;
      setReason(""); setPage(1); setRevision((v) => v + 1); onSaved();
      setMessage("Đã lưu tình trạng cung cấp. Tạo kế hoạch mới để tính tác động; số liệu kế hoạch đang xem giữ nguyên.");
    } catch (e) { if (mounted.current) setError(e as Error); }
    finally { sending.current = false; if (mounted.current) setBusy(false); }
  }
  return <Panel title="Tình trạng cung cấp" note="Quản lý riêng sản phẩm tại kho này. Các ngày được khai báo theo mô phỏng UTC.">
    <label className="supply-date">Ngày mô phỏng (UTC)<input type="date" value={day} disabled={busy} onChange={(e) => onDate(e.target.value)} /></label>
    {!ready ? <p className="notice">Quản lý tình trạng cung cấp chưa được bật. Bạn vẫn có thể xem thông tin sản phẩm.</p> : <>
      <State loading={history.loading} error={history.error} />
      {!day && <p className="notice">Chọn ngày mô phỏng trước khi thao tác.</p>}
      {state && <p>{badge(state.supply_status)} {state.stop_on ? `· Ngày ngừng nhập: ${text(state.stop_on)}` : ""}</p>}
      {stale && <p className="notice">Ngày đang xem trước thay đổi mới nhất. Chọn ngày ghi nhận mới hơn để thao tác.</p>}
      {message && <div className="notice success" role="status" ref={notice} tabIndex={-1}>{message}</div>}
      <form onSubmit={save} aria-label="Thay đổi tình trạng cung cấp" className="supply-form">
        <fieldset disabled={busy || history.loading || !day || !state || !!stale || !!conflict}>
          <p>Ngày ghi nhận: {day || "Chưa chọn"}{action === "stop" ? " · Ngày nhà cung cấp thông báo (mô phỏng)." : " · Hiệu lực trong ngày này."}</p>
          {action === "stop" && <label>Ngày ngừng nhập<input type="date" required min={addSupplyDays(day)} value={stopOn} onChange={(e) => setStopOn(e.target.value)} /></label>}
          <label>Lý do thay đổi<textarea required maxLength={1000} value={reason} onChange={(e) => setReason(e.target.value)} /></label>
          <div className="notice subtle"><strong>{title} · {String(product.sku)} · {warehouseName(product)} · {String(product.product_type)}</strong>
            <p>{action === "stop" ? `Từ ${stopOn || "ngày được chọn"}, không đặt lô mới; vẫn nhận lô đã đặt và bán tồn.` : action === "cancel_stop" ? "Hủy lịch chưa hiệu lực; tiếp tục nhập theo cấu hình sản phẩm." : "Cho nhập lại theo cấu hình có hiệu lực khi tính kế hoạch mới."}</p>
            <p>{stock ? `Kế hoạch đang xem: tồn ${text(stock.closing_qty)}, hàng đang về ${text(stock.pending_qty)}.` : "Chưa có số tồn hoặc lô đang về trong kế hoạch đang xem."} Lô đã đặt vẫn được nhận đúng ETA.</p>
          </div>
          <div className="form-actions"><button className="primary" disabled={busy}>{busy ? "Đang lưu…" : title}</button></div>
        </fieldset>
      </form>
      {error && <div className="notice error" role="alert">{errorLabel(error)}<button type="button" onClick={() => { setError(undefined); setRevision((v) => v + 1); }}>Tải lại tình trạng cung cấp</button></div>}
      <details className="advanced-section"><summary>Lịch sử cung cấp</summary>
        <Table rows={history.data?.items ?? []} columns={[
          {key:"version",label:"Phiên bản"},{key:"action",label:"Thao tác",render:(v) => ({stop:"Lên lịch ngừng",cancel_stop:"Hủy lịch",resume:"Mở nhập lại"}[String(v)] ?? text(v))},
          {key:"known_on",label:"Ngày ghi nhận"},{key:"effective_on",label:"Ngày hiệu lực"},{key:"reason",label:"Lý do"},
        ]} /><Pager page={page} total={history.data?.total ?? 0} onChange={setPage} />
      </details>
    </>}
  </Panel>;
}
