import { useResource } from "../hooks/useResource";
import { State } from "../components/ui/State";
import { Table, type Column } from "../components/ui/Table";
import { Icon } from "../components/ui/Icon";
import { Card } from "../components/ui/Card";
import { AUDIT_ACTIONS } from "./Operations";
import { ORDER_STATUS, localTime, qty, type OpsSummary } from "../operations/types";
import type { Page } from "../types/api";

const LIST = 6;

export function Dashboard({ onNavigate, onOpenOrder }: { onNavigate: (page: string) => void; onOpenOrder: (id: string) => void }) {
  const summary = useResource<OpsSummary>("/operations/summary");
  const orders = useResource<Page>(`/operations/orders?status=open&sort=eta&page_size=${LIST}`);
  const stock = useResource<Page>(`/operations/stock?sort=on_hand&page_size=${LIST}`);
  const audit = useResource<Page>(`/operations/audit?page_size=${LIST}`);
  const today = summary.data?.business_date ?? "";
  // Same stat cards as the simulation pages: [label, value, target page, icon, tone, note]
  const late = Number(summary.data?.late_orders ?? 0);
  const cards: [string, unknown, string, string, string, string][] = [
    ["Tổng tồn sổ", summary.data?.on_hand_units, "stock", "box", "", `${qty(summary.data?.stocked_items ?? 0)} mặt hàng còn tồn`],
    ["Đơn chờ nhận", summary.data?.pending_orders, "orders", "truck", "teal", "Đã xác nhận, chưa nhận đủ"],
    ["Đơn trễ hạn", summary.data?.late_orders, "orders", "alert", late > 0 ? "red" : "", late > 0 ? "Quá ngày dự kiến nhận" : "Không có đơn trễ"],
    ["Đơn nháp", summary.data?.draft_orders, "orders", "clock", "orange", "Chưa xác nhận đặt hàng"],
    ["Yêu cầu đại lý chờ xử lý", summary.data?.pending_dealer_requests, "dealer-requests", "check", "teal", "Chờ duyệt hoặc chờ xuất"],
    ["Phiếu trong ngày", summary.data?.documents_today, "documents", "download", "", "Nhập, xuất và kiểm kê hôm nay"],
  ];
  const orderColumns: Column[] = [
    { key: "number", label: "Đơn nhập", render: (value, row) => <button className="text-button" onClick={() => onOpenOrder(String(row.id))}>{String(value)}</button> },
    { key: "carrier", label: "Nhà cung cấp" },
    // Business date and ETA are both ISO dates, so string comparison is a date comparison.
    { key: "eta", label: "Dự kiến nhận", render: (value) => today && String(value) < today ? <span className="ops-status late">{String(value)} · trễ</span> : String(value) },
    { key: "status", label: "Trạng thái", render: (value) => ORDER_STATUS[String(value)] },
    { key: "received_qty", label: "Đã nhận / đặt", render: (value, row) => `${qty(value)} / ${qty(row.ordered_qty)}` },
  ];
  const stockColumns: Column[] = [
    { key: "sku", label: "Sản phẩm", render: (value, row) => <span><strong>{String(value)}</strong><small className="cell-subtitle">{String(row.name)}</small></span> },
    { key: "warehouse", label: "Kho" },
    { key: "on_hand_qty", label: "Tồn sổ", render: qty },
  ];
  const auditColumns: Column[] = [
    { key: "created_at", label: "Thời gian", render: localTime },
    { key: "actor", label: "Người thực hiện" },
    { key: "action", label: "Thao tác", render: (value) => AUDIT_ACTIONS[String(value)] ?? String(value) },
  ];
  const panel = (title: string, icon: string, target: string, resource: { data?: Page; loading: boolean; error?: Error }, columns: Column[], empty: string) =>
    <section className="panel dashboard-panel">
      <div className="panel-title"><h2 className="dashboard-panel-title"><Icon name={icon} size={18} />{title}</h2><button className="text-button" onClick={() => onNavigate(target)}>Xem tất cả</button></div>
      <State error={resource.error} />
      {!resource.error && <Table rows={resource.data?.items ?? []} loading={resource.loading} columns={columns} label={title} emptyMessage={empty} />}
    </section>;
  return <div className="operations-workspace">
    <div className="ops-section-heading"><div><p className="eyebrow">QUẢN LÝ</p><h1>Tổng quan</h1><p className="caption">Tình hình kho và nhập hàng theo sổ chứng từ{today ? ` · ngày ${today}` : ""}.</p></div></div>
    <State error={summary.error} />
    <div className="stats dashboard-summary" aria-busy={summary.loading}>{cards.map(([label, value, target, icon, tone, note]) =>
      <button key={label} className="stat-button" onClick={() => onNavigate(target)} aria-label={`${label}: ${summary.loading ? "đang tải" : qty(value)}`}>
        <Card label={label} value={summary.loading ? "—" : qty(value)} note={note} icon={icon} tone={tone} /></button>)}</div>
    <div className="dashboard-grid">
      {panel("Đơn nhập sắp về", "truck", "orders", orders, orderColumns, "Không có đơn đang chờ nhận.")}
      {panel("Tồn thấp nhất", "box", "stock", stock, stockColumns, "Chưa có số dư. Nhận hàng hoặc kiểm kê để bắt đầu.")}
      {panel("Thao tác gần đây", "clock", "audit", audit, auditColumns, "Chưa có thao tác nào.")}
    </div>
  </div>;
}
