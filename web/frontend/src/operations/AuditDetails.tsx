import type { Row } from "../types/api";
import { DOCUMENT_KIND, ORDER_STATUS, qty } from "./types";

const LABELS: Record<string, string> = { reason: "Lý do", number: "Số phiếu", kind: "Loại phiếu", lead_time_days: "Thời gian nhập (ngày)", line_count: "Số dòng sản phẩm", name: "Tên mới", old_name: "Tên trước", code: "Mã kho", sku: "SKU", active: "Hoạt động", status: "Trạng thái đơn", quantity_delta: "Thay đổi tồn", version: "Phiên bản", old_eta: "Ngày dự kiến trước", eta: "Ngày dự kiến mới", dealer_request: "Yêu cầu đại lý" };
export const AUDIT_ENTITIES: Record<string, string> = { purchase_order: "Đơn nhập", stock_document: "Chứng từ kho", supplier_settings: "Cấu hình nhà cung cấp", warehouse: "Kho hàng", product: "Sản phẩm", dealer: "Đại lý", dealer_request: "Yêu cầu đại lý" };
export function AuditDetails({ value }: { value: unknown }) {
  const entries = Object.entries((value && typeof value === "object" ? value : {}) as Row).filter(([key]) => key in LABELS);
  if (!entries.length) return <span>Không có thông tin bổ sung</span>;
  return <details><summary>Xem chi tiết</summary><dl className="ops-audit-details">{entries.map(([key, entry]) => <div key={key}><dt>{LABELS[key]}</dt><dd>{key === "kind" ? DOCUMENT_KIND[String(entry)] : key === "status" ? ORDER_STATUS[String(entry)] : key === "active" ? entry ? "Có" : "Không" : typeof entry === "number" ? qty(entry) : String(entry ?? "Không có")}</dd></div>)}</dl></details>;
}
