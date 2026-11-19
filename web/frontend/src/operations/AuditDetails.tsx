import type { Row } from "../types/api";
import { Dialog } from "../components/ui/Dialog";
import { DOCUMENT_KIND, ORDER_STATUS, localTime, qty } from "./types";

const LABELS: Record<string, string> = { reason: "Lý do", number: "Số phiếu", kind: "Loại phiếu", lead_time_days: "Thời gian nhập (ngày)", line_count: "Số dòng sản phẩm", name: "Tên mới", old_name: "Tên trước", code: "Mã", sku: "SKU", active: "Hoạt động", status: "Trạng thái đơn", quantity_delta: "Thay đổi tồn", version: "Phiên bản", old_eta: "Ngày dự kiến trước", eta: "Ngày dự kiến mới", dealer_request: "Yêu cầu đại lý" };
export const AUDIT_ENTITIES: Record<string, string> = { purchase_order: "Đơn nhập", stock_document: "Chứng từ kho", supplier_settings: "Cấu hình nhà cung cấp", warehouse: "Kho hàng", product: "Sản phẩm", dealer: "Đại lý", dealer_request: "Yêu cầu đại lý" };
export const AUDIT_ACTIONS: Record<string, string> = { created: "Tạo mới", registered: "Đăng ký sản phẩm", updated: "Cập nhật", confirm: "Xác nhận đặt hàng", cancel: "Hủy phần chưa nhận", received: "Nhận hàng", posted: "Ghi sổ chứng từ", eta_changed: "Đổi ngày dự kiến nhận", approve: "Duyệt yêu cầu đại lý", reject: "Từ chối yêu cầu đại lý", issue: "Xuất kho cho đại lý", receive: "Đại lý xác nhận nhận" };
// Entities that have their own detail view; the audit dialog links straight to it.
export const AUDIT_LINKS: Record<string, string> = { purchase_order: "Mở đơn nhập", stock_document: "Mở chứng từ", dealer_request: "Mở yêu cầu đại lý" };

function show(key: string, entry: unknown) {
  return key === "kind" ? DOCUMENT_KIND[String(entry)] : key === "status" ? ORDER_STATUS[String(entry)] : key === "active" ? entry ? "Có" : "Không"
    : typeof entry === "number" ? qty(entry) : String(entry ?? "Không có");
}

export function AuditDialog({ row, onClose, onOpen }: { row: Row; onClose: () => void; onOpen: (entity: string, key: string) => void }) {
  const entity = String(row.entity_type), key = String(row.entity_key);
  const details = Object.entries((row.details && typeof row.details === "object" ? row.details : {}) as Row).filter(([name]) => name in LABELS);
  return <Dialog title={`${AUDIT_ACTIONS[String(row.action)] ?? String(row.action)} · ${AUDIT_ENTITIES[entity] ?? "Không có"}`} onClose={onClose} className="operations-form-dialog">
    <div className="operations-form-fields"><dl className="ops-audit-details">
      <div><dt>Thời gian</dt><dd>{localTime(row.created_at)}</dd></div>
      <div><dt>Người thực hiện</dt><dd>{String(row.actor ?? "Không có")}</dd></div>
      <div><dt>Tham chiếu</dt><dd>{key.length > 16 ? key : `#${key}`}</dd></div>
      {details.map(([name, entry]) => <div key={name}><dt>{LABELS[name]}</dt><dd>{show(name, entry)}</dd></div>)}
    </dl>{!details.length && <p className="caption">Không có thông tin bổ sung.</p>}</div>
    <div className="dialog-form-actions"><button type="button" onClick={onClose}>Đóng</button>
      {AUDIT_LINKS[entity] && <button className="primary" type="button" onClick={() => { onClose(); onOpen(entity, key); }}>{AUDIT_LINKS[entity]}</button>}</div>
  </Dialog>;
}
