import { useState } from "react";
import { useResource } from "../hooks/useResource";
import { useDebounce } from "../hooks/useDebounce";
import { apiAllPages } from "../services/http";
import { query } from "../utils/url";
import { Table, type Column } from "../components/ui/Table";
import { Pager } from "../components/ui/Pager";
import { State } from "../components/ui/State";
import { CatalogEditor } from "../operations/CatalogEditor";
import { MovementEditor } from "../operations/MovementEditor";
import { OrderEditor } from "../operations/OrderEditor";
import { OrderDetail } from "../operations/OrderDetail";
import { DocumentDetail } from "../operations/DocumentDetail";
import { AuditDetails, AUDIT_ENTITIES } from "../operations/AuditDetails";
import { Recommendations } from "../operations/Recommendations";
import { DOCUMENT_KIND, ORDER_STATUS, localTime, qty, type OpsSummary, type Product, type Supplier, type Warehouse, type Position } from "../operations/types";
import type { Context } from "../types/context";
import type { Page } from "../types/api";

export const OPERATION_TABS = [["stock", "Tồn kho"], ["recommendations", "Đề xuất nhập"], ["orders", "Đơn nhập"], ["products", "Sản phẩm"], ["warehouses", "Kho hàng"], ["suppliers", "Nhà cung cấp"], ["documents", "Chứng từ"], ["audit", "Lịch sử thao tác"]] as const;
const TAB_INFO: Record<string, [string, string]> = {
  stock: ["KHO", "Số dư theo kho và sản phẩm, cập nhật từ chứng từ đã ghi sổ."],
  documents: ["KHO", "Phiếu nhập, xuất và kiểm kê đã ghi sổ."],
  warehouses: ["KHO", "Danh sách kho vật lý đang quản lý."],
  orders: ["NHẬP HÀNG", "Lập, xác nhận và nhận hàng theo đơn nhập."],
  recommendations: ["NHẬP HÀNG", "Gợi ý lượng nhập từ tồn sổ, đơn đang về và dự báo đã hoàn tất."],
  suppliers: ["NHẬP HÀNG", "Thời gian nhập mặc định của từng nhà cung cấp."],
  products: ["DANH MỤC", "Danh mục SIM/eSIM đang kinh doanh."],
  audit: ["HỆ THỐNG", "Ai đã làm gì, vào lúc nào."],
};

type Editor = { kind: "warehouse"; row?: Warehouse } | { kind: "product"; row?: Product } | { kind: "supplier"; row: Supplier } | { kind: "order" } | { kind: "issue"; row?: Position } | { kind: "count"; row?: Position };
export const AUDIT_ACTIONS: Record<string, string> = { created: "Tạo mới", registered: "Đăng ký sản phẩm", updated: "Cập nhật", confirm: "Xác nhận đặt hàng", cancel: "Hủy phần chưa nhận", received: "Nhận hàng", posted: "Ghi sổ chứng từ" };

export function Operations({ ctx, onContext }: { ctx: Context; onContext: (patch: Partial<Context>) => void }) {
  const tab = OPERATION_TABS.some(([key]) => key === ctx.opsTab) ? ctx.opsTab! : "stock";
  const [page, setPage] = useState(1), [search, setSearch] = useState(""), [status, setStatus] = useState(""), [warehouse, setWarehouse] = useState("");
  const [editor, setEditor] = useState<Editor>(), [document, setDocument] = useState("");
  const debounced = useDebounce(search);
  const summary = useResource<OpsSummary>("/operations/summary");
  const suppliers = useResource<Page<Supplier>>("/operations/suppliers?page_size=100", false, 0, apiAllPages);
  const warehouses = useResource<Page<Warehouse>>("/operations/warehouses?active=true&page_size=100", false, 0, apiAllPages);
  const path = `/operations/${tab}?${query({ page, page_size: 25, ...(["stock", "orders", "products"].includes(tab) ? { search: debounced } : {}), ...(tab === "orders" ? { status } : {}), ...(tab === "products" ? { include_inactive: "true" } : {}), ...(tab === "stock" ? { warehouse_id: warehouse } : {}) })}`;
  const result = useResource<Page>(tab === "recommendations" || ctx.opsOrderId && tab === "orders" ? null : path);
  const activeWarehouses = warehouses.data?.items ?? [], supplierRows = suppliers.data?.items ?? [];
  function openOrder(id: string) { onContext({ opsTab: "orders", opsOrderId: id }); }
  const canCreateOrder = !!activeWarehouses.length && !!supplierRows.length && !warehouses.error && !suppliers.error;
  const columns: Record<string, Column[]> = {
    stock: [{ key: "sku", label: "Sản phẩm", render: (value, row) => <span><strong>{String(value)}</strong><small className="cell-subtitle">{String(row.name)}</small></span> }, { key: "warehouse", label: "Kho" }, { key: "on_hand_qty", label: "Tồn sổ", render: qty }, { key: "last_movement_on", label: "Biến động gần nhất" }, { key: "item_id", label: "Thao tác", render: (_, row) => <div className="ops-actions"><button disabled={Number(row.on_hand_qty) <= 0} onClick={() => setEditor({ kind: "issue", row: row as Position })}>Xuất kho</button><button onClick={() => setEditor({ kind: "count", row: row as Position })}>Kiểm kê</button></div> }],
    orders: [{ key: "number", label: "Đơn nhập", render: (value, row) => <button className="text-button" onClick={() => openOrder(String(row.id))}>{String(value)}</button> }, { key: "carrier", label: "Nhà cung cấp" }, { key: "status", label: "Trạng thái", render: (value) => <span className={`ops-status ${value}`}>{ORDER_STATUS[String(value)]}</span> }, { key: "eta", label: "Dự kiến nhận" }, { key: "ordered_qty", label: "Đã đặt", render: qty }, { key: "received_qty", label: "Đã nhận", render: qty }],
    products: [{ key: "sku", label: "SKU" }, { key: "name", label: "Tên sản phẩm" }, { key: "product_type", label: "Loại", render: (value) => value === "physical_SIM" ? "SIM vật lý" : "eSIM" }, { key: "carrier", label: "Nhà cung cấp" }, { key: "destination_country", label: "Quốc gia sử dụng" }, { key: "active", label: "Trạng thái", render: (value) => value ? "Hoạt động" : "Ngừng nhập" }, { key: "id", label: "Thao tác", render: (_, row) => <button onClick={() => setEditor({ kind: "product", row: row as Product })}>Chỉnh sửa</button> }],
    warehouses: [{ key: "code", label: "Mã kho" }, { key: "name", label: "Tên kho" }, { key: "country", label: "Quốc gia" }, { key: "active", label: "Trạng thái", render: (value) => value ? "Hoạt động" : "Đã đóng" }, { key: "id", label: "Thao tác", render: (_, row) => <button onClick={() => setEditor({ kind: "warehouse", row: row as Warehouse })}>Chỉnh sửa</button> }],
    suppliers: [{ key: "carrier", label: "Nhà cung cấp" }, { key: "lead_time_days", label: "Thời gian nhập", render: (value) => `${value} ngày` }, { key: "id", label: "Thao tác", render: (_, row) => <button onClick={() => setEditor({ kind: "supplier", row: row as Supplier })}>Đổi thời gian nhập</button> }],
    documents: [{ key: "number", label: "Số phiếu", render: (value, row) => <button className="text-button" onClick={() => setDocument(String(row.id))}>{String(value)}</button> }, { key: "kind", label: "Loại", render: (value) => DOCUMENT_KIND[String(value)] }, { key: "occurred_on", label: "Ngày nghiệp vụ" }, { key: "external_ref", label: "Phiếu đối chiếu" }, { key: "actor", label: "Người ghi sổ" }, { key: "created_at", label: "Ghi sổ lúc", render: localTime }],
    audit: [{ key: "created_at", label: "Thời gian", render: localTime }, { key: "actor", label: "Người thực hiện" }, { key: "action", label: "Thao tác", render: (value) => AUDIT_ACTIONS[String(value)] ?? String(value) }, { key: "entity_type", label: "Đối tượng", render: (value) => AUDIT_ENTITIES[String(value)] ?? "Không có" }, { key: "entity_key", label: "Tham chiếu", render: (value) => <span title={String(value)}>{String(value).length > 16 ? String(value).slice(0, 8) : `#${value}`}</span> }, { key: "details", label: "Nội dung", render: (value) => <AuditDetails value={value} /> }],
  };
  const [group, caption] = TAB_INFO[tab];
  return <div className="operations-workspace"><div className="ops-section-heading"><div><p className="eyebrow">{group}</p><h1>{OPERATION_TABS.find(([key]) => key === tab)?.[1]}</h1><p className="caption">{caption}</p></div></div>
    <State error={summary.error} />
    {tab === "recommendations" ? <Recommendations /> : tab === "orders" && ctx.opsOrderId ? <OrderDetail key={ctx.opsOrderId} id={ctx.opsOrderId} today={summary.data?.business_date ?? ""} suppliers={supplierRows} warehouses={activeWarehouses} onBack={() => onContext({ opsOrderId: undefined })} /> : <section className="panel ops-list-panel">
      <div className="ops-section-heading"><h2>Danh sách</h2><div className="ops-actions">
        {tab === "orders" && <button className="primary" disabled={!canCreateOrder} onClick={() => setEditor({ kind: "order" })}>Tạo đơn nhập</button>}
        {tab === "stock" && <button className="primary" disabled={!activeWarehouses.length} onClick={() => setEditor({ kind: "count" })}>Kiểm kê / tồn đầu</button>}
        {tab === "products" && <button className="primary" onClick={() => setEditor({ kind: "product" })}>Thêm sản phẩm</button>}
        {tab === "warehouses" && <button className="primary" onClick={() => setEditor({ kind: "warehouse" })}>Thêm kho</button>}
      </div></div>
      {tab === "suppliers" && <p className="caption">Nhà cung cấp được tạo khi đăng ký sản phẩm. Thay thời gian nhập chỉ áp dụng cho đơn lập mới.</p>}
      {tab === "orders" && !canCreateOrder && !warehouses.loading && !suppliers.loading && <p className="notice">Để tạo đơn, thêm kho đang hoạt động và sản phẩm có nhà cung cấp trước.</p>}
      {["stock", "orders", "products"].includes(tab) && <div className="ops-filters"><label>Tìm kiếm<input value={search} maxLength={120} placeholder={tab === "orders" ? "Mã đơn hoặc nhà cung cấp" : "Mã hoặc tên sản phẩm"} onChange={(event) => { setSearch(event.target.value); setPage(1); }} /></label>
        {tab === "orders" && <label>Trạng thái<select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><option value="">Tất cả</option>{Object.entries(ORDER_STATUS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>}
        {tab === "stock" && <label>Kho hàng<select value={warehouse} onChange={(event) => { setWarehouse(event.target.value); setPage(1); }}><option value="">Tất cả kho</option>{activeWarehouses.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>}
      </div>}
      <State error={result.error ?? warehouses.error ?? suppliers.error} />
      {!result.error && <><Table rows={result.data?.items ?? []} loading={result.loading} stickyFirstColumn columns={columns[tab]} label={`${OPERATION_TABS.find(([key]) => key === tab)?.[1]}, cuộn trong bảng`} emptyMessage={tab === "stock" ? "Chưa có số dư phù hợp. Nhận hàng hoặc ghi nhận kiểm kê để bắt đầu theo dõi tồn." : "Không có dữ liệu phù hợp."} /><Pager page={page} total={result.data?.total ?? 0} pageSize={25} onChange={setPage} /></>}
    </section>}
    {editor && (editor.kind === "order" ? <OrderEditor suppliers={supplierRows} warehouses={activeWarehouses} today={summary.data?.business_date ?? ""} onClose={() => setEditor(undefined)} onSaved={(order) => { setEditor(undefined); openOrder(String(order.id)); }} />
      : editor.kind === "count" || editor.kind === "issue" ? <MovementEditor kind={editor.kind} initial={editor.row} warehouses={activeWarehouses} today={summary.data?.business_date ?? ""} onClose={() => setEditor(undefined)} />
      : <CatalogEditor kind={editor.kind} row={editor.row} onClose={() => setEditor(undefined)} />)}
    {document && <DocumentDetail id={document} onClose={() => setDocument("")} />}
  </div>;
}
