import type { Column } from "../components/ui/Table";
import { qty, type Product } from "./types";

export const productType = (value: unknown) => value === "physical_SIM" ? "SIM vật lý" : "eSIM";

/** Catalog columns shared by the product list and the supplier detail page. */
export function productColumns({ onPolicy, onEdit, onSupplier, showSupplier = true }: {
  onPolicy: (row: Product) => void; onEdit: (row: Product) => void; onSupplier?: (id: string) => void; showSupplier?: boolean;
}): Column[] {
  return [
    { key: "sku", label: "Sản phẩm", render: (value, row) => <span><strong>{String(row.name)}</strong><small className="cell-subtitle">{String(value)}</small></span> },
    { key: "product_type", label: "Loại", render: productType },
    ...(showSupplier ? [{ key: "carrier", label: "Nhà cung cấp", render: (value, row) => onSupplier
      ? <button className="text-button" onClick={(event) => { event.stopPropagation(); onSupplier(String(row.supplier_id)); }}>{String(value)}</button> : String(value) } satisfies Column] : []),
    { key: "destination_country", label: "Quốc gia sử dụng" },
    { key: "on_hand_qty", label: "Tồn hiện có", render: qty },
    { key: "fixed_order_qty", label: "Lượng nhập / ROP tối thiểu", render: (value, row) => value == null ? <span className="cell-muted">Chưa thiết lập</span>
      : <span>{qty(value)} <small className="cell-subtitle">ROP ≥ {qty(row.configured_rop_floor)}</small></span> },
    { key: "lead_time_days", label: "Thời gian nhập", render: (value) => `${value} ngày` },
    { key: "active", label: "Trạng thái", render: (value) => <span className={`ops-status ${value ? "received" : "cancelled"}`}>{value ? "Hoạt động" : "Ngừng nhập"}</span> },
    { key: "id", label: "Thao tác", render: (_, row) => <div className="ops-actions">
      <button onClick={(event) => { event.stopPropagation(); onPolicy(row as Product); }}>Chính sách nhập</button>
      <button onClick={(event) => { event.stopPropagation(); onEdit(row as Product); }}>Chỉnh sửa</button></div> },
  ];
}
