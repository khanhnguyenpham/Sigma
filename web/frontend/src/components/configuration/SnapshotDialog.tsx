import { useId, useRef, useState, type KeyboardEvent } from "react";
import type { Page, Row, Run } from "../../types/api";
import { useResource } from "../../hooks/useResource";
import { fmt } from "../../utils/format";
import { State } from "../ui/State";
import { Table } from "../ui/Table";
import { Pager } from "../ui/Pager";
import { Dialog } from "../ui/Dialog";

interface Snapshot {
  scenario: Row; parameters: Row; versions: Row; policies: Page; policy_overrides: Row[];
  receipts_initial: Row[]; supply_schedule: { internal_stops: Row[]; provider_stops: Row[] };
}
const tabs = [["summary", "Tổng quan"], ["policies", "Chính sách"], ["receipts", "Lô đầu kỳ"], ["supply", "Lịch cung cấp"]] as const;
type Tab = typeof tabs[number][0];
const missing = (value: unknown) => value == null || value === "" ? "Không có" : String(value);
const days = (value: unknown) => value == null ? "Không có" : `${String(value)} ngày`;

export function SnapshotDialog({ run, title, onClose }: { run: Run; title: string; onClose: () => void }) {
  const [tab, setTab] = useState<Tab>("summary");
  const [page, setPage] = useState(1);
  const id = useId();
  const nav = useRef<HTMLElement>(null);
  const snapshot = useResource<Snapshot>(`/runs/${run.id}/snapshot?page=${page}&page_size=25`);
  const data = snapshot.data;
  function moveTab(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const target = event.key === "ArrowRight" ? (index + 1) % tabs.length
      : event.key === "ArrowLeft" ? (index + tabs.length - 1) % tabs.length
      : event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : -1;
    if (target < 0) return;
    event.preventDefault(); setTab(tabs[target][0]);
    nav.current?.querySelectorAll<HTMLButtonElement>("[role=tab]")[target].focus();
  }
  return <Dialog title={title} onClose={onClose} className="snapshot-dialog">
    <nav ref={nav} className="snapshot-tabs" role="tablist" aria-label="Nội dung cấu hình">
      {tabs.map(([key, name], index) => <button type="button" key={key} role="tab" id={`${id}-${key}-tab`}
        aria-controls={`${id}-panel`} aria-selected={tab === key} tabIndex={tab === key ? 0 : -1}
        onKeyDown={(event) => moveTab(event, index)} onClick={() => setTab(key)}>{name}</button>)}
    </nav>
    <div className="snapshot-content" key={tab} id={`${id}-panel`} role="tabpanel" aria-labelledby={`${id}-${tab}-tab`} tabIndex={0}>
      <State loading={snapshot.loading} error={snapshot.error} />
      {data && <>
        {tab === "summary" && <>
          <p className="snapshot-explanation">Cấu hình tại lúc tạo lượt {run.id.slice(0, 8)}. Thay đổi hiện tại không sửa kết quả đã lưu.</p>
          <dl className="snapshot-facts">
            <div><dt>Ngày chốt UTC</dt><dd>{run.as_of_date}</dd></div>
            <div><dt>Kịch bản</dt><dd>{missing(data.scenario.name)}{data.scenario.version != null && ` · v${String(data.scenario.version)}`}</dd></div>
            <div><dt>Số ngày phủ tồn đầu</dt><dd>{missing(data.parameters.cover_days)}</dd></div>
            <div><dt>Lịch sử tính tồn đầu</dt><dd>{days(data.parameters.initial_stock_history_days)}</dd></div>
            {data.parameters.zero_sales_fallback_days != null && <div><dt>Dự phòng nếu 28 ngày không bán</dt><dd>{days(data.parameters.zero_sales_fallback_days)} khi đủ quan sát</dd></div>}
            <div><dt>Hệ số tồn an toàn</dt><dd>{missing(data.parameters.safety_multiplier)}</dd></div>
            <div><dt>Thời gian nhập hàng</dt><dd>{days(data.parameters.lead_time_days)}</dd></div>
            <div><dt>Chu kỳ xét nhập</dt><dd>{days(data.parameters.review_days)}</dd></div>
            <div><dt>Phạm vi dự kiến</dt><dd>{days(data.parameters.horizon_days)}</dd></div>
            <div><dt>Phiên bản cấu hình</dt><dd>{missing(data.versions.config)}</dd></div>
            <div><dt>Quy tắc tồn kho</dt><dd>{missing(data.versions.inventory_policy)}</dd></div>
            <div><dt>Phiên bản giả định</dt><dd>{missing(data.versions.assumption)}</dd></div>
            <div><dt>Phiên bản mục tiêu</dt><dd>{missing(data.versions.target)}</dd></div>
            <div><dt>Quy tắc kho nhận</dt><dd>{missing(data.versions.receiving_warehouse)}</dd></div>
          </dl>
          <details className="snapshot-source"><summary>Nguồn & thông tin phương án</summary><dl className="snapshot-facts">
            <div><dt>Mã phương án</dt><dd>{run.id}</dd></div><div><dt>Quan sát đến</dt><dd>{missing(run.observation_end)}</dd></div>
            <div><dt>Nguồn dữ liệu</dt><dd>{missing(run.source_import_run_id)}</dd></div><div><dt>Dự báo cha</dt><dd>{missing(run.forecast_run_id)}</dd></div>
            {!!data.versions.runtime_code_reference && <div><dt>Phiên bản phần mềm</dt><dd>{missing((data.versions.runtime_code_reference as Row).version)}</dd></div>}
          </dl><p>Dữ liệu lịch sử; tồn và nhập là mô phỏng.</p></details>
        </>}
        {tab === "policies" && <>
          <h3>Chính sách đã chốt ({fmt(data.policies.total)})</h3>
          <Table stickyFirstColumn rows={data.policies.items} columns={[
            { key: "sku", label: "Sản phẩm" }, { key: "product_type", label: "Loại" }, { key: "carrier", label: "Nhà mạng" },
            { key: "version", label: "Phiên bản" }, { key: "effective_from", label: "Áp dụng từ" },
            { key: "configured_rop_floor", label: "Ngưỡng tối thiểu" }, { key: "fixed_order_qty", label: "Lượng mỗi lô" },
            { key: "safety_days", label: "Ngày dự phòng" }, { key: "moq", label: "MOQ lịch sử" },
            { key: "warning_horizon_days", label: "Cảnh báo trước (ngày)" }, { key: "safety_mode", label: "Cách tính tồn an toàn" },
            { key: "rop_mode", label: "Cách tính ngưỡng nhập" }, { key: "receiving_warehouse_id", label: "Mã kho nhận" },
          ]} />
          <Pager page={page} total={data.policies.total} pageSize={25} onChange={setPage} />
          <details className="snapshot-overrides"><summary>Điều chỉnh riêng ({fmt(data.policy_overrides.length)})</summary>
            <Table stickyFirstColumn rows={data.policy_overrides} columns={[
              { key: "item_id", label: "Mã mặt hàng" }, { key: "configured_rop_floor", label: "Ngưỡng tối thiểu" },
              { key: "fixed_order_qty", label: "Lượng mỗi lô" }, { key: "safety_days", label: "Ngày dự phòng" },
              { key: "warning_horizon_days", label: "Ngày cảnh báo trước" }, { key: "moq", label: "MOQ lịch sử" },
              { key: "safety_mode", label: "Cách tính tồn an toàn" }, { key: "safety_lookback_days", label: "Lịch sử tính an toàn" },
              { key: "safety_factor", label: "Hệ số an toàn" }, { key: "rop_mode", label: "Cách tính ngưỡng nhập" },
            ]} />
          </details>
        </>}
        {tab === "receipts" && <><h3>Lô đầu kỳ đã biết</h3><Table stickyFirstColumn rows={data.receipts_initial} columns={[
          { key: "item_id", label: "Mã mặt hàng" }, { key: "ordered_on", label: "Ngày đặt" },
          { key: "eta", label: "Ngày nhận dự kiến" }, { key: "ordered_qty", label: "Số lượng" },
        ]} /></>}
        {tab === "supply" && ([['internal_stops', 'Lịch ngừng nhập nội bộ'], ['provider_stops', 'Lịch nhà cung cấp ngừng dịch vụ']] as const).map(([key, name]) =>
          <section key={key}><h3>{name}</h3><Table stickyFirstColumn rows={data.supply_schedule[key]} columns={[
            { key: "item_id", label: "Mã mặt hàng" }, { key: "known_on", label: "Ngày biết" },
            { key: "effective_on", label: "Ngày hiệu lực" }, { key: "reason", label: "Lý do" },
          ]} /></section>)}
      </>}
    </div>
  </Dialog>;
}
