import { useEffect, useState } from "react";
import type { Page, Row, Run } from "../types/api";
import type { Context, PurchasingView } from "../types/context";
import { useResource } from "../hooks/useResource";
import { query } from "../utils/url";
import { fmt, text } from "../utils/format";
import { warehouseName } from "../utils/warehouse";
import { Panel } from "../components/ui/Panel";
import { Table } from "../components/ui/Table";
import { Pager } from "../components/ui/Pager";
import { State } from "../components/ui/State";
import { ProductPolicyForm } from "../components/products/ProductPolicyForm";
import { InventoryInformation } from "../components/inventory/InventoryDetails";
import { inventoryKinds } from "../config/navigation";

export function Products({ onOpen }: { onOpen: (row: Row) => void }) {
  const [search, setSearch] = useState(""), [warehouse, setWarehouse] = useState(""), [type, setType] = useState(""), [page, setPage] = useState(1);
  const warehouses = useResource<Page>("/warehouses?page_size=100");
  const data = useResource<Page>(`/products?${query({ search: search.trim(), warehouse_id: warehouse, product_type: type, page, page_size: 50 })}`);
  function filter(setter: (value: string) => void, value: string) { setter(value); setPage(1); }
  return <>
    <div className="page-intro"><h1>Sản phẩm</h1><p>Quản lý thông tin sản phẩm, lượng nhập mỗi lần và mức tồn an toàn.</p></div>
    <Panel title="Danh sách sản phẩm" note="Chọn một sản phẩm để xem thông tin và chỉnh sửa cấu hình nhập hàng.">
      <div className="product-filters">
        <label>Tìm sản phẩm<input type="search" value={search} placeholder="Nhập mã SKU" onChange={(e) => filter(setSearch, e.target.value)} /></label>
        <label>Kho sản phẩm<select value={warehouse} onChange={(e) => filter(setWarehouse, e.target.value)}><option value="">Tất cả kho</option>{warehouses.data?.items.map((w) => <option key={String(w.id)} value={String(w.id)}>{warehouseName(w)}</option>)}</select></label>
        <label>Loại sản phẩm<select value={type} onChange={(e) => filter(setType, e.target.value)}><option value="">Tất cả loại</option><option>eSIM</option><option>physical_SIM</option></select></label>
      </div>
      <State loading={warehouses.loading} error={warehouses.error} />
      <State loading={data.loading} error={data.error} empty={!data.loading && !data.error && !data.data?.items.length} />
      {data.data && <><Table rows={data.data.items} onRow={onOpen} columns={[
        { key: "sku", label: "Mã sản phẩm", render: (v) => <strong>{String(v)}</strong> },
        { key: "product_type", label: "Loại" }, { key: "city", label: "Kho" }, { key: "carrier", label: "Nhà mạng" },
        { key: "policy", label: "Lượng nhập mỗi lần", render: (v) => (v as Row | null)?.fixed_order_qty == null ? "Chưa cấu hình" : fmt((v as Row).fixed_order_qty) },
        { key: "safety_days", label: "Tồn an toàn", render: (_, r) => { const p = r.policy as Row | null; return !p ? "Chưa cấu hình" : `${fmt(p.safety_days)} ngày`; } },
      ]} /><Pager page={page} total={data.data.total} onChange={setPage} /></>}
    </Panel>
  </>;
}

export function ProductDetail({ ctx, run, onNavigate, onWarehouse, onItem }: {
  ctx: Context; run?: Run; onNavigate: (page: string) => void; onWarehouse: (row: Row) => void;
  onItem: (row: Row, page?: string, view?: PurchasingView) => void;
}) {
  const [revision, setRevision] = useState(0), [message, setMessage] = useState("");
  const product = useResource<Row>(ctx.itemId ? `/products/${ctx.itemId}?v=${revision}` : null);
  const ready = run?.status === "complete" && inventoryKinds.includes(run.kind) && !!ctx.origin;
  const stock = useResource<Page>(ready && product.data
    ? `/runs/${run.id}/inventory?${query({ item_id: product.data.id as number, date_from: ctx.origin, date_to: ctx.origin })}` : null);
  useEffect(() => setMessage(""), [ctx.itemId]);
  const row = product.data, policy = row?.policy as Row | null;
  return <>
    <nav className="warehouse-breadcrumb" aria-label="Đường dẫn sản phẩm"><button className="text-button" onClick={() => onNavigate("products")}>← Sản phẩm</button>{row && <><span>/</span><button className="text-button" onClick={() => onWarehouse(row)}>Kho {warehouseName(row)}</button><span>/</span><span aria-current="page">{String(row.sku)}</span></>}</nav>
    <State loading={product.loading} error={product.error} />
    {!ctx.itemId && <div className="notice" role="status">Chọn sản phẩm từ danh sách để xem thông tin.</div>}
    {row && <>
      <div className="page-heading"><div><h1>{String(row.sku)}</h1><p>{String(row.product_type)} · {warehouseName(row)} · {String(row.carrier)}</p></div></div>
      {message && <div className="notice success" role="status">{message}</div>}
      <div className="product-layout">
        <Panel title="Thông tin sản phẩm"><dl className="product-information">
          <div><dt>Mã sản phẩm</dt><dd>{String(row.sku)}</dd></div><div><dt>Loại sản phẩm</dt><dd>{String(row.product_type)}</dd></div>
          <div><dt>Kho</dt><dd>{warehouseName(row)}</dd></div><div><dt>Quốc gia</dt><dd>{String(row.destination_country)}</dd></div>
          <div><dt>Nhà cung cấp</dt><dd>{String(row.carrier)}</dd></div><div><dt>Ngày có dữ liệu</dt><dd>{text(row.first_seen_date)}</dd></div>
          <div><dt>Cấu hình áp dụng từ</dt><dd>{text(policy?.effective_from)}</dd></div>
        </dl><button className="secondary" onClick={() => onWarehouse(row)}>Xem sản phẩm trong kho</button></Panel>
        <Panel title="Cấu hình nhập hàng" note="Thiết lập riêng cho sản phẩm tại kho này.">
          <ProductPolicyForm key={`${row.id}:${revision}:${policy?.version ?? 0}`} product={row} onSaved={() => { setRevision((v) => v + 1); setMessage("Đã lưu cấu hình sản phẩm."); }} onReload={() => { setRevision((v) => v + 1); setMessage(""); }} />
        </Panel>
      </div>
      {ready && <Panel title="Tình trạng tồn kho" note={`Số liệu trong kế hoạch tại ngày ${ctx.origin}. Lưu cấu hình không tính lại số liệu đã lưu.`}>
        <State loading={stock.loading} error={stock.error} empty={!stock.loading && !stock.error && !stock.data?.items.length} />
        {stock.data?.items[0] && <InventoryInformation focused={{ ...stock.data.items[0], display_city: row.city }} onItem={onItem} />}
      </Panel>}
    </>}
  </>;
}
