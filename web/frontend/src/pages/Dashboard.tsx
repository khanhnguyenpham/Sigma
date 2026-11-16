import { useResource } from "../hooks/useResource";
import { State } from "../components/ui/State";
import { Table, type Column } from "../components/ui/Table";
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
  const cards: [string, unknown, string][] = [
    ["Tổng tồn sổ", summary.data?.on_hand_units, "stock"],
    ["Đơn chờ nhận", summary.data?.pending_orders, "orders"],
    ["Đơn trễ hạn", summary.data?.late_orders, "orders"],
    ["Đơn nháp", summary.data?.draft_orders, "orders"],
    ["Phiếu trong ngày", summary.data?.documents_today, "documents"],
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
  const panel = (title: string, target: string, resource: { data?: Page; loading: boolean; error?: Error }, columns: Column[], empty: string) =>
    <section className="panel dashboard-panel">
      <div className="panel-title"><h2>{title}</h2><button className="text-button" onClick={() => onNavigate(target)}>Xem tất cả</button></div>
      <State error={resource.error} />
      {!resource.error && <Table rows={resource.data?.items ?? []} loading={resource.loading} columns={columns} label={title} emptyMessage={empty} />}
    </section>;
  return <div className="operations-workspace">
    <div className="ops-section-heading"><div><p className="eyebrow">QUẢN LÝ</p><h1>Tổng quan</h1><p className="caption">Tình hình kho và nhập hàng theo sổ chứng từ{today ? ` · ngày ${today}` : ""}.</p></div></div>
    <State error={summary.error} />
    <div className="ops-summary dashboard-summary" aria-busy={summary.loading}>{cards.map(([label, value, target]) =>
      <button key={label} onClick={() => onNavigate(target)}><span>{label}</span><strong>{summary.loading ? "…" : qty(value)}</strong></button>)}</div>
    <div className="dashboard-grid">
      {panel("Đơn nhập sắp về", "orders", orders, orderColumns, "Không có đơn đang chờ nhận.")}
      {panel("Tồn thấp nhất", "stock", stock, stockColumns, "Chưa có số dư. Nhận hàng hoặc kiểm kê để bắt đầu.")}
      {panel("Thao tác gần đây", "audit", audit, auditColumns, "Chưa có thao tác nào.")}
    </div>
  </div>;
}
