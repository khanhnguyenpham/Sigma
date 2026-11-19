import { useState } from "react";
import { useResource } from "../hooks/useResource";
import { useDebounce } from "../hooks/useDebounce";
import { apiAllPages } from "../services/http";
import { query } from "../utils/url";
import { Table, type Column } from "../components/ui/Table";
import { Pager } from "../components/ui/Pager";
import { State } from "../components/ui/State";
import { Card } from "../components/ui/Card";
import { CatalogEditor } from "../operations/CatalogEditor";
import { MovementEditor } from "../operations/MovementEditor";
import { OrderEditor } from "../operations/OrderEditor";
import { OrderDetail } from "../operations/OrderDetail";
import { DocumentDetail } from "../operations/DocumentDetail";
import { AuditDialog, AUDIT_ACTIONS, AUDIT_ENTITIES } from "../operations/AuditDetails";
import { ProductPolicyDialog } from "../operations/ProductPolicyDialog";
import { SupplierDetail } from "../operations/SupplierDetail";
import { WarehouseCards } from "../operations/WarehouseCards";
import { FilterBar, PRODUCT_STATUS, PRODUCT_TYPES, productStatusParams, type FilterField } from "../operations/Filters";
import { productColumns, productType } from "../operations/productColumns";
import { AdminRequest } from "./Dealers";
import { Recommendations } from "../operations/Recommendations";
import type { Row } from "../types/api";
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
  suppliers: ["DANH MỤC", "Nhà mạng cung cấp SIM/eSIM. Mở một nhà cung cấp để xem và chỉnh sản phẩm, lượng nhập, ngưỡng của họ."],
  products: ["DANH MỤC", "Danh mục SIM/eSIM đang kinh doanh."],
  audit: ["HỆ THỐNG", "Ai đã làm gì, vào lúc nào."],
};

type Editor = { kind: "warehouse"; row?: Warehouse } | { kind: "product"; row?: Product; carrier?: string } | { kind: "policy"; row: Product } | { kind: "supplier"; row: Supplier } | { kind: "order" } | { kind: "issue"; row?: Position } | { kind: "count"; row?: Position };
export { AUDIT_ACTIONS };
const options = (record: Record<string, string>) => Object.entries(record);

export function Operations({ ctx, onContext }: { ctx: Context; onContext: (patch: Partial<Context>) => void }) {
  const tab = OPERATION_TABS.some(([key]) => key === ctx.opsTab) ? ctx.opsTab! : "stock";
  const [page, setPage] = useState(1), [filters, setFilters] = useState<Record<string, string>>({});
  const [editor, setEditor] = useState<Editor>(), [document, setDocument] = useState("");
  const [auditRow, setAuditRow] = useState<Row>(), [dealerRequest, setDealerRequest] = useState("");
  const search = useDebounce(filters.search ?? "");
  const summary = useResource<OpsSummary>("/operations/summary");
  const suppliers = useResource<Page<Supplier>>("/operations/suppliers?page_size=100", false, 0, apiAllPages);
  const warehouses = useResource<Page<Warehouse>>("/operations/warehouses?active=true&page_size=100", false, 0, apiAllPages);
  const catalog = useResource<{ countries: string[]; suppliers: { id: number; carrier: string }[] }>(
    ["stock", "orders", "products", "suppliers"].includes(tab) ? "/operations/product-filters" : null);
  // Tồn kho opens on warehouse cards; a chosen warehouse (?ops_warehouse=) shows its balances.
  const stockWarehouse = tab === "stock" ? ctx.opsWarehouseId : undefined;
  const warehouseCards = tab === "stock" && !stockWarehouse;
  const detail = (tab === "orders" && ctx.opsOrderId) || (tab === "suppliers" && ctx.opsSupplierId) || warehouseCards;
  const { status = "", ...rest } = filters;
  const params = tab === "products" ? { ...rest, ...productStatusParams(status) } : tab === "warehouses" ? { ...rest, active: status === "" ? undefined : String(status === "active") } : filters;
  const path = `/operations/${tab}?${query({ page, page_size: 25, ...params, search, warehouse_id: stockWarehouse })}`;
  const result = useResource<Page>(tab === "recommendations" || detail ? null : path, true);
  const activeWarehouses = warehouses.data?.items ?? [], supplierRows = suppliers.data?.items ?? [];
  const supplierOptions = (catalog.data?.suppliers ?? []).map((row) => [String(row.id), row.carrier] as const);
  const countryOptions = (catalog.data?.countries ?? []).map((name) => [name, name] as const);
  function openOrder(id: string) { onContext({ opsTab: "orders", opsOrderId: id }); }
  function openSupplier(id?: string) { onContext({ opsTab: "suppliers", opsSupplierId: id }); }
  function openWarehouse(id?: string) { setFilters({}); setPage(1); onContext({ opsTab: "stock", opsWarehouseId: id }); }
  function openEntity(entity: string, key: string) {
    if (entity === "purchase_order") openOrder(key);
    else if (entity === "stock_document") setDocument(key);
    else if (entity === "dealer_request") setDealerRequest(key);
  }
  function change(key: string, value: string) { setFilters((current) => ({ ...current, [key]: value })); setPage(1); }
  // Whole rows open their detail; the visible number/button stays for clarity.
  const onRow: Record<string, (row: Row) => void> = {
    orders: (row) => openOrder(String(row.id)), documents: (row) => setDocument(String(row.id)), audit: (row) => setAuditRow(row),
    suppliers: (row) => openSupplier(String(row.id)), products: (row) => setEditor({ kind: "policy", row: row as Product }),
  };
  const fields: Record<string, FilterField[]> = {
    stock: [{ key: "search", label: "Tìm kiếm", type: "search", placeholder: "Mã hoặc tên sản phẩm" },
      { key: "supplier_id", label: "Nhà cung cấp", type: "select", options: supplierOptions, all: "Tất cả nhà cung cấp" },
      { key: "product_type", label: "Loại", type: "select", options: PRODUCT_TYPES },
      { key: "sort", label: "Sắp xếp", type: "select", options: [["on_hand", "Tồn thấp trước"]], all: "Theo kho" }],
    orders: [{ key: "search", label: "Tìm kiếm", type: "search", placeholder: "Mã đơn hoặc nhà cung cấp" },
      { key: "status", label: "Trạng thái", type: "select", options: [["open", "Đang chờ nhận (mọi trạng thái mở)"], ...options(ORDER_STATUS)] },
      { key: "supplier_id", label: "Nhà cung cấp", type: "select", options: supplierOptions, all: "Tất cả nhà cung cấp" },
      { key: "sort", label: "Sắp xếp", type: "select", options: [["eta", "Ngày dự kiến nhận gần nhất"]], all: "Mới tạo trước" }],
    products: [{ key: "search", label: "Tìm kiếm", type: "search", placeholder: "Mã hoặc tên sản phẩm" },
      { key: "supplier_id", label: "Nhà cung cấp", type: "select", options: supplierOptions, all: "Tất cả nhà cung cấp" },
      { key: "country", label: "Quốc gia sử dụng", type: "select", options: countryOptions, all: "Tất cả quốc gia" },
      { key: "product_type", label: "Loại", type: "select", options: PRODUCT_TYPES },
      { key: "status", label: "Trạng thái", type: "select", options: PRODUCT_STATUS }],
    suppliers: [{ key: "search", label: "Tìm kiếm", type: "search", placeholder: "Tên nhà mạng" },
      { key: "country", label: "Quốc gia sử dụng", type: "select", options: countryOptions, all: "Tất cả quốc gia" }],
    warehouses: [{ key: "status", label: "Trạng thái", type: "select", options: [["active", "Hoạt động"], ["inactive", "Đã đóng"]] }],
    documents: [{ key: "search", label: "Tìm kiếm", type: "search", placeholder: "Số phiếu hoặc phiếu đối chiếu" },
      { key: "kind", label: "Loại phiếu", type: "select", options: options(DOCUMENT_KIND) },
      { key: "date_from", label: "Từ ngày", type: "date" }, { key: "date_to", label: "Đến ngày", type: "date" }],
    audit: [{ key: "entity_type", label: "Đối tượng", type: "select", options: options(AUDIT_ENTITIES) },
      { key: "action", label: "Thao tác", type: "select", options: options(AUDIT_ACTIONS) },
      { key: "date_from", label: "Từ ngày", type: "date" }, { key: "date_to", label: "Đến ngày", type: "date" }],
  };
  const canCreateOrder = !!activeWarehouses.length && !!supplierRows.length && !warehouses.error && !suppliers.error;
  const editProduct = { onPolicy: (row: Product) => setEditor({ kind: "policy", row }), onEdit: (row: Product) => setEditor({ kind: "product", row }) };
  const columns: Record<string, Column[]> = {
    stock: [{ key: "sku", label: "Sản phẩm", render: (value, row) => <span><strong>{String(value)}</strong><small className="cell-subtitle">{String(row.name)}</small></span> }, { key: "product_type", label: "Loại", render: productType }, { key: "carrier", label: "Nhà cung cấp" }, { key: "warehouse", label: "Kho" }, { key: "on_hand_qty", label: "Tồn sổ", render: qty }, { key: "last_movement_on", label: "Biến động gần nhất" }, { key: "item_id", label: "Thao tác", render: (_, row) => <div className="ops-actions"><button disabled={Number(row.on_hand_qty) <= 0} onClick={() => setEditor({ kind: "issue", row: row as Position })}>Xuất kho</button><button onClick={() => setEditor({ kind: "count", row: row as Position })}>Kiểm kê</button></div> }],
    orders: [{ key: "number", label: "Đơn nhập", render: (value, row) => <button className="text-button" onClick={(event) => { event.stopPropagation(); openOrder(String(row.id)); }}>{String(value)}</button> }, { key: "carrier", label: "Nhà cung cấp" }, { key: "status", label: "Trạng thái", render: (value) => <span className={`ops-status ${value}`}>{ORDER_STATUS[String(value)]}</span> }, { key: "ordered_on", label: "Ngày đặt" }, { key: "eta", label: "Dự kiến nhận" }, { key: "ordered_qty", label: "Đã đặt", render: qty }, { key: "received_qty", label: "Đã nhận", render: qty }],
    products: productColumns({ ...editProduct, onSupplier: openSupplier }),
    warehouses: [{ key: "code", label: "Mã kho" }, { key: "name", label: "Tên kho" }, { key: "country", label: "Quốc gia" }, { key: "active", label: "Trạng thái", render: (value) => <span className={`ops-status ${value ? "received" : "cancelled"}`}>{value ? "Hoạt động" : "Đã đóng"}</span> }, { key: "id", label: "Thao tác", render: (_, row) => <button onClick={() => setEditor({ kind: "warehouse", row: row as Warehouse })}>Chỉnh sửa</button> }],
    suppliers: [{ key: "carrier", label: "Nhà cung cấp", render: (value, row) => <span><strong className="link-text">{String(value)}</strong><small className="cell-subtitle">{(row.countries as string[] | null)?.join(", ") || "Chưa có sản phẩm"}</small></span> },
      { key: "product_count", label: "Sản phẩm", render: (value, row) => <span>{qty(value)}{row.active_product_count != null && <small className="cell-subtitle">{qty(row.active_product_count)} đang hoạt động</small>}</span> },
      { key: "on_hand_qty", label: "Tồn hiện có", render: qty }, { key: "lead_time_days", label: "Thời gian nhập", render: (value) => `${value} ngày` },
      { key: "id", label: "Thao tác", render: (_, row) => <div className="ops-actions"><button onClick={(event) => { event.stopPropagation(); openSupplier(String(row.id)); }}>Xem chi tiết</button>
        <button onClick={(event) => { event.stopPropagation(); setEditor({ kind: "supplier", row: row as Supplier }); }}>Đổi thời gian nhập</button></div> }],
    documents: [{ key: "number", label: "Số phiếu", render: (value, row) => <button className="text-button" onClick={(event) => { event.stopPropagation(); setDocument(String(row.id)); }}>{String(value)}</button> }, { key: "kind", label: "Loại", render: (value) => DOCUMENT_KIND[String(value)] }, { key: "occurred_on", label: "Ngày nghiệp vụ" }, { key: "external_ref", label: "Phiếu đối chiếu" }, { key: "actor", label: "Người ghi sổ" }, { key: "created_at", label: "Ghi sổ lúc", render: localTime }],
    audit: [{ key: "created_at", label: "Thời gian", render: localTime }, { key: "actor", label: "Người thực hiện" }, { key: "action", label: "Thao tác", render: (value) => AUDIT_ACTIONS[String(value)] ?? String(value) }, { key: "entity_type", label: "Đối tượng", render: (value) => AUDIT_ENTITIES[String(value)] ?? "Không có" }, { key: "entity_key", label: "Tham chiếu", render: (value) => <span title={String(value)}>{String(value).length > 16 ? String(value).slice(0, 8) : `#${value}`}</span> }, { key: "details", label: "Nội dung", render: () => <span className="link-text">Xem chi tiết</span> }],
  };
  const [group, caption] = TAB_INFO[tab];
  const chosenWarehouse = stockWarehouse ? activeWarehouses.find((row) => String(row.id) === stockWarehouse) : undefined;
  // Headline cards in the same style as the simulation pages; values come from data already loaded on this page.
  const sd = summary.data, sum = (key: "product_count" | "active_product_count") => supplierRows.reduce((total, row) => total + Number(row[key] ?? 0), 0);
  const leads = supplierRows.map((row) => row.lead_time_days);
  const stats: Record<string, [string, string, string, string, string][]> = {
    stock: chosenWarehouse ? [["Mặt hàng còn tồn", qty(chosenWarehouse.stocked_items ?? 0), "Số dư lớn hơn 0", "box", ""], ["Tồn hiện có", qty(chosenWarehouse.on_hand_qty ?? 0), "Theo chứng từ đã ghi sổ", "grid", "teal"],
      ["Đang về", qty(chosenWarehouse.incoming_qty ?? 0), "Còn lại trên đơn đã xác nhận", "truck", ""], ["Mặt hàng đã hết", qty(chosenWarehouse.empty_items ?? 0), "Từng có tồn, nay bằng 0", "alert", Number(chosenWarehouse.empty_items) > 0 ? "orange" : ""]]
      : [["Kho đang hoạt động", qty(activeWarehouses.length), "Nhận và xuất hàng", "warehouse", ""], ["Mặt hàng còn tồn", qty(sd?.stocked_items), "Số dư lớn hơn 0", "box", ""],
      ["Tổng tồn sổ", qty(sd?.on_hand_units), "Mọi kho, theo chứng từ", "grid", "teal"], ["Phiếu trong ngày", qty(sd?.documents_today), "Nhập, xuất và kiểm kê", "download", ""]],
    orders: [["Đơn chờ nhận", qty(sd?.pending_orders), "Đã xác nhận, chưa nhận đủ", "truck", "teal"], ["Đơn trễ hạn", qty(sd?.late_orders), "Quá ngày dự kiến nhận", "alert", Number(sd?.late_orders) > 0 ? "red" : ""],
      ["Đơn nháp", qty(sd?.draft_orders), "Chưa xác nhận đặt hàng", "clock", "orange"]],
    products: [["Sản phẩm", qty(sum("product_count")), `${qty(sum("active_product_count"))} đang hoạt động`, "box", ""], ["Nhà cung cấp", qty(catalog.data?.suppliers?.length ?? 0), "Nhà mạng có sản phẩm", "truck", ""],
      ["Quốc gia sử dụng", qty(catalog.data?.countries?.length ?? 0), "Điểm đến của SIM/eSIM", "grid", "teal"]],
    suppliers: [["Nhà cung cấp", qty(supplierRows.length), `${qty(supplierRows.filter((row) => Number(row.product_count) > 0).length)} có sản phẩm`, "truck", ""],
      ["Sản phẩm", qty(sum("product_count")), "Thuộc mọi nhà cung cấp", "box", ""],
      ["Thời gian nhập", leads.length ? `${Math.min(...leads)}–${Math.max(...leads)} ngày` : "—", "Ngắn nhất – dài nhất", "clock", "orange"]],
  };
  const supplierDetail = tab === "suppliers" && ctx.opsSupplierId;
  return <div className="operations-workspace"><div className="ops-section-heading"><div><p className="eyebrow">{group}</p><h1>{OPERATION_TABS.find(([key]) => key === tab)?.[1]}</h1><p className="caption">{caption}</p></div></div>
    <State error={summary.error} />
    {tab === "recommendations" ? <Recommendations />
      : tab === "orders" && ctx.opsOrderId ? <OrderDetail key={ctx.opsOrderId} id={ctx.opsOrderId} today={summary.data?.business_date ?? ""} suppliers={supplierRows} warehouses={activeWarehouses} onBack={() => onContext({ opsOrderId: undefined })} />
      : supplierDetail ? <SupplierDetail key={supplierDetail} id={supplierDetail} supplier={supplierRows.find((row) => String(row.id) === supplierDetail)} onBack={() => openSupplier(undefined)}
        onLead={(row) => setEditor({ kind: "supplier", row })} onAdd={(row) => setEditor({ kind: "product", carrier: row.carrier })} {...editProduct} />
      : <>{stockWarehouse && <nav className="warehouse-breadcrumb" aria-label="Đường dẫn kho">
          <button className="text-button" onClick={() => openWarehouse(undefined)}><span aria-hidden="true">←</span> Danh sách kho</button>
          <span aria-hidden="true">/</span><span aria-current="page">{chosenWarehouse?.name ?? "Kho"}</span></nav>}
        {stats[tab] && <div className={`stats stats-${stats[tab].length}`}>{stats[tab].map(([label, value, note, icon, tone]) =>
        <Card key={label} label={label} value={summary.loading || suppliers.loading || warehouses.loading ? "—" : value} note={note} icon={icon} tone={tone} />)}</div>}
      {warehouseCards ? <WarehouseCards warehouses={activeWarehouses} loading={warehouses.loading} error={warehouses.error} onChoose={openWarehouse} onAdd={() => setEditor({ kind: "count" })} />
      : <section className="panel ops-list-panel">
      <div className="ops-section-heading"><h2>{chosenWarehouse ? `Sản phẩm tại ${chosenWarehouse.name}` : "Danh sách"}</h2><div className="ops-actions">
        {tab === "orders" && <button className="primary" disabled={!canCreateOrder} onClick={() => setEditor({ kind: "order" })}>Tạo đơn nhập</button>}
        {tab === "stock" && <button className="primary" disabled={!activeWarehouses.length} onClick={() => setEditor({ kind: "count" })}>Kiểm kê / tồn đầu</button>}
        {tab === "products" && <button className="primary" onClick={() => setEditor({ kind: "product" })}>Thêm sản phẩm</button>}
        {tab === "warehouses" && <button className="primary" onClick={() => setEditor({ kind: "warehouse" })}>Thêm kho</button>}
      </div></div>
      {tab === "suppliers" && <p className="caption">Nhà cung cấp được tạo khi đăng ký sản phẩm. Thời gian nhập (mặc định 7 ngày) áp dụng cho mọi sản phẩm của nhà cung cấp đó: đơn nhập lập mới, đề xuất nhập và kịch bản mô phỏng tạo sau khi lưu. Đơn và kịch bản đã có giữ thời gian đã chốt.</p>}
      {tab === "orders" && !canCreateOrder && !warehouses.loading && !suppliers.loading && <p className="notice">Để tạo đơn, thêm kho đang hoạt động và sản phẩm có nhà cung cấp trước.</p>}
      {fields[tab] && <FilterBar fields={fields[tab]} values={filters} onChange={change} onReset={() => { setFilters({}); setPage(1); }} />}
      <State error={result.error ?? warehouses.error ?? suppliers.error} />
      {!result.error && <><Table rows={result.data?.items ?? []} loading={result.loading} onRow={onRow[tab]} stickyFirstColumn columns={columns[tab]} label={`${OPERATION_TABS.find(([key]) => key === tab)?.[1]}, cuộn trong bảng`} emptyMessage={tab === "stock" && !Object.values(filters).some(Boolean) ? "Chưa có số dư phù hợp. Nhận hàng hoặc ghi nhận kiểm kê để bắt đầu theo dõi tồn." : "Không có dữ liệu phù hợp với bộ lọc."} /><Pager page={page} total={result.data?.total ?? 0} pageSize={25} loading={result.loading} onChange={setPage} /></>}
    </section>}</>}
    {editor && (editor.kind === "order" ? <OrderEditor suppliers={supplierRows} warehouses={activeWarehouses} today={summary.data?.business_date ?? ""} onClose={() => setEditor(undefined)} onSaved={(order) => { setEditor(undefined); openOrder(String(order.id)); }} />
      : editor.kind === "count" || editor.kind === "issue" ? <MovementEditor kind={editor.kind} initial={editor.row} warehouses={activeWarehouses} today={summary.data?.business_date ?? ""} onClose={() => setEditor(undefined)} />
      : editor.kind === "policy" ? <ProductPolicyDialog product={editor.row} supplier={supplierRows.find((row) => row.id === editor.row.supplier_id)} onClose={() => setEditor(undefined)} />
      : <CatalogEditor kind={editor.kind} row={editor.row} carrier={editor.kind === "product" ? editor.carrier : undefined} onClose={() => setEditor(undefined)} />)}
    {document && <DocumentDetail id={document} onClose={() => setDocument("")} />}
    {auditRow && <AuditDialog row={auditRow} onClose={() => setAuditRow(undefined)} onOpen={openEntity} />}
    {dealerRequest && <AdminRequest id={dealerRequest} onClose={() => setDealerRequest("")} />}
  </div>;
}
