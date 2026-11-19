import { useState } from "react";
import { useResource } from "../hooks/useResource";
import { useDebounce } from "../hooks/useDebounce";
import { query } from "../utils/url";
import { Table } from "../components/ui/Table";
import { Pager } from "../components/ui/Pager";
import { State } from "../components/ui/State";
import { FilterBar, PRODUCT_STATUS, PRODUCT_TYPES, productStatusParams } from "./Filters";
import { productColumns } from "./productColumns";
import { qty, type Product, type Supplier } from "./types";
import type { Page } from "../types/api";

/** One supplier (carrier): headline numbers, lead time and every product it supplies, editable in place. */
export function SupplierDetail({ id, supplier, onBack, onLead, onPolicy, onEdit, onAdd }: {
  id: string; supplier?: Supplier; onBack: () => void; onLead: (row: Supplier) => void;
  onPolicy: (row: Product) => void; onEdit: (row: Product) => void; onAdd: (row: Supplier) => void;
}) {
  const [page, setPage] = useState(1), [filters, setFilters] = useState<Record<string, string>>({});
  const search = useDebounce(filters.search ?? "");
  const products = useResource<Page<Product>>(`/operations/products?${query({ supplier_id: id, page, page_size: 25, search,
    product_type: filters.product_type, country: filters.country, ...productStatusParams(filters.status ?? "") })}`, true);
  const countries = supplier?.countries ?? [];
  const change = (key: string, value: string) => { setFilters((current) => ({ ...current, [key]: value })); setPage(1); };
  return <>
    <div className="supplier-detail-heading">
      <button type="button" className="text-button" onClick={onBack}>← Tất cả nhà cung cấp</button>
      <div className="ops-section-heading"><div><h2>{supplier?.carrier ?? "Nhà cung cấp"}</h2>
        <p className="caption">{countries.length ? `Cung cấp cho ${countries.join(", ")}` : "Chưa có sản phẩm đăng ký"}</p></div>
        {supplier && <div className="ops-actions"><button onClick={() => onLead(supplier)}>Đổi thời gian nhập</button>
          <button className="primary" onClick={() => onAdd(supplier)}>Thêm sản phẩm</button></div>}</div>
    </div>
    {supplier && <div className="ops-summary">
      <div><span>Sản phẩm</span><strong>{qty(supplier.product_count ?? 0)}</strong><small>{qty(supplier.active_product_count ?? 0)} đang hoạt động</small></div>
      <div><span>Quốc gia</span><strong>{countries.length}</strong></div>
      <div><span>Tồn hiện có</span><strong>{qty(supplier.on_hand_qty ?? 0)}</strong><small>tổng mọi kho</small></div>
      <div><span>Thời gian nhập</span><strong>{supplier.lead_time_days} ngày</strong><small>áp cho mọi sản phẩm</small></div>
    </div>}
    <section className="panel ops-list-panel" aria-label={`Sản phẩm của ${supplier?.carrier ?? "nhà cung cấp"}`}>
      <div className="ops-section-heading"><h2>Sản phẩm</h2></div>
      <FilterBar values={filters} onChange={change} onReset={() => { setFilters({}); setPage(1); }} fields={[
        { key: "search", label: "Tìm kiếm", type: "search", placeholder: "Mã hoặc tên sản phẩm" },
        { key: "product_type", label: "Loại", type: "select", options: PRODUCT_TYPES },
        { key: "country", label: "Quốc gia sử dụng", type: "select", options: countries.map((name) => [name, name] as const), all: "Tất cả quốc gia" },
        { key: "status", label: "Trạng thái", type: "select", options: PRODUCT_STATUS },
      ]} />
      <State error={products.error} />
      {!products.error && <><Table rows={products.data?.items ?? []} loading={products.loading} stickyFirstColumn label="Sản phẩm của nhà cung cấp, cuộn trong bảng"
        columns={productColumns({ onPolicy, onEdit, showSupplier: false })} onRow={(row) => onPolicy(row as Product)} emptyMessage="Không có sản phẩm phù hợp." />
        <Pager page={page} total={products.data?.total ?? 0} pageSize={25} loading={products.loading} onChange={setPage} /></>}
    </section>
  </>;
}
