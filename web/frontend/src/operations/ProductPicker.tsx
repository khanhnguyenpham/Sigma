import { useState } from "react";
import { useResource } from "../hooks/useResource";
import { useDebounce } from "../hooks/useDebounce";
import { query } from "../utils/url";
import { Table } from "../components/ui/Table";
import { Pager } from "../components/ui/Pager";
import { State } from "../components/ui/State";
import type { Page } from "../types/api";
import type { Product } from "./types";

export function ProductPicker({ supplierId, onPick, includeInactive = false }: { supplierId?: number; onPick: (product: Product) => void; includeInactive?: boolean }) {
  const [search, setSearch] = useState(""), [page, setPage] = useState(1);
  const debounced = useDebounce(search);
  const resource = useResource<Page<Product>>(supplierId === 0 ? null : `/operations/products?${query({ supplier_id: supplierId, search: debounced, page, page_size: 10, include_inactive: includeInactive ? "true" : undefined })}`);
  return <div className="ops-product-picker"><label>Tìm sản phẩm<input value={search} maxLength={120} placeholder="Nhập mã hoặc tên sản phẩm" onChange={(event) => { setSearch(event.target.value); setPage(1); }} /></label>
    <State error={resource.error} />
    {!resource.error && <><Table label="Chọn sản phẩm" rows={resource.data?.items ?? []} loading={resource.loading} emptyMessage={supplierId === 0 ? "Chọn nhà cung cấp trước." : "Không có sản phẩm phù hợp. Bạn có thể thêm tại mục Sản phẩm."} columns={[
      { key: "sku", label: "Mã / tên", render: (value, row) => <span>{String(value)}<small className="cell-subtitle">{String(row.name)} · {String(row.destination_country)} · {row.product_type === "physical_SIM" ? "SIM vật lý" : "eSIM"}</small></span> },
      { key: "id", label: "Chọn", render: (_, row) => <button type="button" onClick={() => onPick(row as Product)}>Chọn</button> },
    ]} /><Pager page={page} total={resource.data?.total ?? 0} pageSize={10} onChange={setPage} /></>}
  </div>;
}
