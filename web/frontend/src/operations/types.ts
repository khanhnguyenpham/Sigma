import type { Row } from "../types/api";

export interface OpsSummary { business_date: string; pending_orders: number; late_orders?: number; pending_dealer_requests?: number; draft_orders: number; stocked_items: number; on_hand_units: number | string; documents_today: number }
export interface Supplier extends Row { id: number; carrier: string; lead_time_days: number; version: number; product_count?: number }
export interface Warehouse extends Row { id: number; code: string; name: string; country: string; active: boolean; version: number }
export interface Product extends Row { id: number; name: string; sku: string; product_type: string; carrier: string; supplier_id: number; destination_country: string; active: boolean; version: number; lead_time_days?: number }
export interface OrderLine extends Row { id: number; item_id: number; warehouse_id: number; sku: string; name: string; warehouse: string; ordered_qty: number; received_qty: number; remaining_qty: number }
export interface Order extends Row { planned_eta?: string; id: number; number: string; supplier_id: number; carrier: string; ordered_on: string; eta: string; lead_time_days: number; version: number; status: string; note: string; lines: OrderLine[] }
export interface Position extends Row { warehouse_id: number; item_id: number; warehouse: string; sku?: string; name: string; on_hand_qty: number; version: number }
export interface StockDocument extends Row { id: string; number: string; kind: string; occurred_on: string; external_ref: string; reason: string; created_at: string; lines: Row[] }

export const ORDER_STATUS: Record<string, string> = { draft: "Nháp", ordered: "Chờ nhận", partially_received: "Nhận một phần", received: "Đã nhận đủ", cancelled: "Đã hủy" };
export const DOCUMENT_KIND: Record<string, string> = { receipt: "Nhập kho", issue: "Xuất kho", adjustment: "Kiểm kê" };
export function qty(value: unknown) {
  if (value == null || !/^-?\d+$/.test(String(value))) return "Không có";
  try { return new Intl.NumberFormat("vi-VN").format(BigInt(String(value))); } catch { return "Không có"; }
}
export const localTime = (value: unknown) => value ? new Date(String(value)).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" }) : "Không có";
