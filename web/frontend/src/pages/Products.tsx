import { useEffect, useRef, useState } from "react";
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
import { ProductReceivingForm } from "../components/products/ProductReceivingForm";
import { InventoryInformation } from "../components/inventory/InventoryDetails";
import { inventoryKinds } from "../config/navigation";
import { ProductStatus } from "../components/products/ProductStatus";
import { Icon } from "../components/ui/Icon";

export function Products({ onOpen, onSupply = onOpen, ctx, onContext }: { onOpen: (row: Row) => void; onSupply?: (row: Row) => void; ctx?: Context; onContext?: (patch: Partial<Context>) => void }) {
  const [search, setSearch] = useState("");
  const [warehouse, setWarehouse] = useState(ctx?.warehouseId ?? "");
  const [type, setType] = useState(ctx?.productType ?? "");
  const [carrier, setCarrier] = useState(ctx?.carrier ?? "");
  const [status, setStatus] = useState(ctx?.internalStatus ?? "");
  const [provider, setProvider] = useState(ctx?.providerStatus ?? "");
  const [page, setPage] = useState(1);
  const [supplyReady, setSupplyReady] = useState(false), [tradeReady, setTradeReady] = useState(false);
  const day = ctx?.origin || new Date().toISOString().slice(0,10);
  useEffect(() => setWarehouse(ctx?.warehouseId ?? ""), [ctx?.warehouseId]);
  useEffect(() => setType(ctx?.productType ?? ""), [ctx?.productType]);
  useEffect(() => setCarrier(ctx?.carrier ?? ""), [ctx?.carrier]);
  useEffect(() => {setStatus(ctx?.internalStatus ?? "");setProvider(ctx?.providerStatus ?? "");setPage(1);}, [ctx?.internalStatus,ctx?.providerStatus]);
  const warehouses = useResource<Page>("/warehouses?page_size=100");
  const carriers = [...new Set(warehouses.data?.items.map(w=>String(w.carrier)))].sort();
  const data = useResource<Page>(`/products?${query({search:search.trim(),warehouse_id:warehouse,product_type:type,carrier,page,page_size:50,as_of_date:supplyReady?day:undefined,supply_status:!tradeReady&&supplyReady?status:undefined,internal_status:tradeReady?status:undefined,provider_status:tradeReady?provider:undefined})}`);
  useEffect(() => {if(data.data?.items.length){setSupplyReady(data.data.items[0].supply_schema_ready===true);setTradeReady(data.data.items[0].trade_schema_ready===true);}},[data.data]);
  function filter(setter: (value: string) => void, value: string) {setter(value);setPage(1);}
  function clear() {setSearch("");setWarehouse("");setType("");setCarrier("");setStatus("");setProvider("");setPage(1);onContext?.({warehouseId:"",itemId:"",productType:"",carrier:"",internalStatus:"",providerStatus:""});}
  return <>
    <div className="page-intro"><h1>Sản phẩm</h1><p>Quản lý cấu hình nhập hàng và lịch cung cấp theo từng sản phẩm.</p></div>
    <div className="product-catalog"><Panel title="Danh sách sản phẩm" note="Chọn Cấu hình để chỉnh thông số, hoặc Lịch cung cấp để quản lý lịch ngừng và mở lại.">
      <div className="catalog-filters" role="search" aria-label="Bộ lọc sản phẩm">
        <label className="catalog-search">Tìm sản phẩm<div className="catalog-search-input"><Icon name="search" size={17}/><input type="search" value={search} placeholder="Nhập mã sản phẩm…" onChange={e=>filter(setSearch,e.target.value)}/></div></label>
        <label>Kho sản phẩm<select value={warehouse} onChange={e=>{filter(setWarehouse,e.target.value);onContext?.({warehouseId:e.target.value,itemId:""});}}><option value="">Tất cả kho</option>{warehouses.data?.items.filter(w=>!carrier||w.carrier===carrier).map(w=><option key={String(w.id)} value={String(w.id)}>{warehouseName(w)}</option>)}</select></label>
        <label>Nhà mạng<select value={carrier} onChange={e=>{filter(setCarrier,e.target.value);setWarehouse("");onContext?.({carrier:e.target.value,warehouseId:"",itemId:""});}}><option value="">Tất cả nhà mạng</option>{carriers.map(value=><option key={value}>{value}</option>)}</select></label>
        <label>Loại sản phẩm<select value={type} onChange={e=>{filter(setType,e.target.value);onContext?.({productType:e.target.value,itemId:""});}}><option value="">Tất cả loại</option><option value="eSIM">eSIM</option><option value="physical_SIM">SIM vật lý</option></select></label>
        <label>Trạng thái nhập<select value={status} disabled={!supplyReady} onChange={e=>{filter(setStatus,e.target.value);onContext?.({internalStatus:e.target.value});}}><option value="">Tất cả trạng thái nhập</option><option value="active">Đang nhập hàng</option><option value="scheduled_stop">Sắp ngừng nhập</option><option value="stopped">Đã ngừng nhập</option></select></label>
        <label>Trạng thái<select value={provider} disabled={!tradeReady} onChange={e=>{filter(setProvider,e.target.value);onContext?.({providerStatus:e.target.value});}}><option value="">Tất cả trạng thái</option><option value="clear">Đang cung cấp</option><option value="scheduled_stop">Sắp ngừng cung cấp</option><option value="stopped">Đã ngừng cung cấp</option><option value="scheduled_resume">Chờ cung cấp lại</option></select></label>
      </div>
      <div className="catalog-results"><span>{data.data?<><strong>{fmt(data.data.total)}</strong> sản phẩm</>:"Đang tải sản phẩm…"}<small>Trạng thái theo mốc kế hoạch {day}</small></span><button className="text-button" onClick={clear}>Xóa bộ lọc</button></div>
      <State loading={warehouses.loading} error={warehouses.error}/>
      <State loading={data.loading} error={data.error} empty={!data.loading&&!data.error&&!data.data?.items.length}/>
      {data.data&&<><Table rows={data.data.items} columns={[
        {key:"sku",label:"Sản phẩm",render:(v,r)=><><button className="product-name" onClick={()=>onOpen(r)}>{String(v)}</button><small className="product-cell-note">{r.product_type==="physical_SIM"?"SIM vật lý":"eSIM"}</small></>},
        {key:"city",label:"Kho / nhà mạng",render:(v,r)=><><strong>{String(v)}</strong><small className="product-cell-note">{String(r.carrier)}</small></>},
        {key:"receiving_warehouse",label:"Kho nhận mặc định",render:(v,r)=><>{warehouseName((v ?? r.warehouse) as Row)}{r.receiving_source==="inherited"&&<small className="product-cell-note">Theo kho sản phẩm</small>}</>},
        {key:"internal_status",label:"Trạng thái nhập",render:(v,r)=><ProductStatus kind="internal" value={v??r.supply_status}/>},
        {key:"provider_status",label:"Trạng thái",render:v=><ProductStatus kind="provider" value={v}/>},
        {key:"policy",label:"Cấu hình nhập",render:v=>{const p=v as Row|null;return p?<><strong>{p.fixed_order_qty==null?"Chưa cấu hình":`${fmt(p.fixed_order_qty)} / lần`}</strong><small className="product-cell-note">Tồn an toàn {fmt(p.safety_days)} ngày</small></>:"Chưa cấu hình";}},
        {key:"actions",label:"Thao tác",render:(_,r)=><div className="product-actions"><button className="secondary" aria-label={`Cấu hình ${r.sku} ${r.product_type} tại ${r.city}`} onClick={()=>onOpen(r)}><Icon name="settings" size={15}/>Cấu hình</button><button className="secondary" aria-label={`Lịch cung cấp ${r.sku} ${r.product_type} tại ${r.city}`} onClick={()=>onSupply(r)}><Icon name="clock" size={15}/>Lịch cung cấp</button></div>},
      ]}/><Pager page={page} total={data.data.total} onChange={setPage}/></>}
    </Panel></div>
  </>;
}

export function ProductDetail({ ctx, run, onNavigate, onWarehouse, onItem, onDate }: {
  ctx: Context; run?: Run; onDate?: (day: string) => void; onNavigate: (page: string) => void; onWarehouse: (row: Row) => void;
  onItem: (row: Row, page?: string, view?: PurchasingView) => void;
}) {
  const [revision, setRevision] = useState(0), [message, setMessage] = useState("");
  const [day, setDay] = useState(ctx.origin);
  const notice = useRef<HTMLDivElement>(null);
  useEffect(() => setDay(ctx.origin), [ctx.origin, ctx.itemId]);
  const product = useResource<Row>(ctx.itemId ? `/products/${ctx.itemId}?${query({as_of_date:day})}` : null,true,revision);
  const ready = run?.status === "complete" && inventoryKinds.includes(run.kind) && !!ctx.origin;
  const stock = useResource<Page>(ready && product.data
    ? `/runs/${run.id}/inventory?${query({ item_id: product.data.id as number, date_from: ctx.origin, date_to: ctx.origin })}` : null);
  useEffect(() => {setMessage("");}, [ctx.itemId]);
  useEffect(() => { if (message) notice.current?.focus(); }, [message, product.data?.id]);
  const row = String(product.data?.id)===ctx.itemId?product.data:undefined, policy = row?.policy as Row | null;
  return <>
    <nav className="warehouse-breadcrumb" aria-label="Đường dẫn sản phẩm"><button className="text-button" onClick={() => onNavigate("products")}>← Sản phẩm</button>{row && <><span>/</span><button className="text-button" onClick={() => onWarehouse(row)}>Kho {warehouseName(row)}</button><span>/</span><span aria-current="page">{String(row.sku)}</span></>}</nav>
    <State loading={product.loading} error={product.error} />
    {!ctx.itemId && <div className="notice" role="status">Chọn sản phẩm từ danh sách để xem thông tin.</div>}
    {row && <>
      <div className="page-heading product-page-heading"><div><h1>{String(row.sku)}</h1><p>{String(row.product_type)} · {warehouseName(row)} · {String(row.carrier)}</p></div><button className="secondary" onClick={()=>onItem(row,"product-supply")}><Icon name="clock" size={16}/>Lịch cung cấp</button></div>
      {message && <div className="notice success" role="status" ref={notice} tabIndex={-1}>{message}</div>}
      <div className="product-layout">
        <div className="product-settings-summary">
        <Panel title="Thông tin sản phẩm"><dl className="product-information">
          <div><dt>Mã sản phẩm</dt><dd>{String(row.sku)}</dd></div><div><dt>Loại sản phẩm</dt><dd>{String(row.product_type)}</dd></div>
          <div><dt>Kho danh mục / tuyến nguồn</dt><dd>{warehouseName(row)}</dd></div><div><dt>Quốc gia</dt><dd>{String(row.destination_country)}</dd></div>
          <div><dt>Kho nhận mặc định</dt><dd>{warehouseName((row.receiving_warehouse ?? row.warehouse) as Row)}</dd></div>
          <div><dt>Nhà cung cấp</dt><dd>{String(row.carrier)}</dd></div><div><dt>Ngày có dữ liệu</dt><dd>{text(row.first_seen_date)}</dd></div>
          <div><dt>Cấu hình áp dụng từ</dt><dd>{text(policy?.effective_from)}</dd></div>
        </dl><button className="secondary" onClick={() => onWarehouse(stock.data?.items[0] ? {
          ...row, warehouse_id: stock.data.items[0].receiving_warehouse_id ?? row.warehouse_id,
        } : row)}>Xem sản phẩm trong kho</button></Panel>
        <Panel title="Kho nhận hàng" note="Áp dụng tự động cho các lượt chạy mới.">
          <ProductReceivingForm key={`receiving:${row.id}:${revision}:${row.receiving_version ?? 0}`} product={row}
            onSaved={() => { setRevision((v) => v + 1); setMessage("Đã lưu kho nhận mặc định. Áp dụng cho lượt chạy mới."); }}
            onReload={() => { setRevision((v) => v + 1); setMessage(""); }} />
        </Panel>
        </div>
        <Panel title="Cấu hình nhập hàng" note="Thiết lập riêng cho sản phẩm tại kho này.">
          <ProductPolicyForm key={`${row.id}:${revision}:${policy?.version ?? 0}`} product={row} onSaved={() => { setRevision((v) => v + 1); setMessage("Đã lưu cấu hình sản phẩm."); }} onReload={() => { setRevision((v) => v + 1); setMessage(""); }} />
        </Panel>
      </div>
      {ready && <details className="advanced-section"><summary>Tồn kho trong kế hoạch đang chọn</summary><Panel title="Tình trạng tồn kho" note={`Số liệu trong kế hoạch tại ngày ${ctx.origin}. Lưu cấu hình không tính lại số liệu đã lưu.`}>
        <State loading={stock.loading} error={stock.error} empty={!stock.loading && !stock.error && !stock.data?.items.length} />
        {stock.data?.items[0] && <InventoryInformation focused={{ ...stock.data.items[0], display_city: row.city }} onItem={onItem} />}
      </Panel></details>}
    </>}
  </>;
}
