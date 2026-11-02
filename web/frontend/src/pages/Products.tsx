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
import { InventoryInformation } from "../components/inventory/InventoryDetails";
import { ProductSupplyForm } from "../components/products/ProductSupplyForm";
import { badge } from "../components/ui/Badge";
import { SellThrough } from "../components/forecast/SellThrough";
import { inventoryKinds } from "../config/navigation";
import { TradeRights } from "../components/products/TradePresentation";
import { internalLabel, providerLabel, isTradeRun } from "../utils/trade";

export function Products({ onOpen, ctx, onContext }: { onOpen: (row: Row) => void; ctx?: Context; onContext?: (patch: Partial<Context>) => void }) {
  const [search, setSearch] = useState(""), [warehouse, setWarehouse] = useState(ctx?.warehouseId ?? ""), [type, setType] = useState(ctx?.productType ?? ""), [page, setPage] = useState(1);
  const [day, setDay] = useState(ctx?.origin ?? ""), [status, setStatus] = useState(ctx?.internalStatus ?? ""), [provider,setProvider]=useState(ctx?.providerStatus ?? ""), [supplyReady, setSupplyReady] = useState(false),[tradeReady,setTradeReady]=useState(false);
  useEffect(() => setDay(ctx?.origin ?? ""), [ctx?.origin]);
  useEffect(() => setWarehouse(ctx?.warehouseId ?? ""), [ctx?.warehouseId]);
  useEffect(() => setType(ctx?.productType ?? ""), [ctx?.productType]);
  const warehouses = useResource<Page>("/warehouses?page_size=100");
  const data = useResource<Page>(`/products?${query({ search: search.trim(), warehouse_id: warehouse, product_type: type, page, page_size: 50, as_of_date: supplyReady ? day : undefined, supply_status: !tradeReady && supplyReady && day ? status : undefined,internal_status:tradeReady && day?status:undefined,provider_status:tradeReady && day?provider:undefined })}`);
  useEffect(() => { if (data.data?.items.length) {setSupplyReady(data.data.items[0].supply_schema_ready === true);setTradeReady(data.data.items[0].trade_schema_ready === true);} }, [data.data]);
  useEffect(()=>{setStatus(ctx?.internalStatus ?? "");setProvider(ctx?.providerStatus ?? "");setPage(1);},[ctx?.internalStatus,ctx?.providerStatus]);
  function filter(setter: (value: string) => void, value: string) { setter(value); setPage(1); }
  return <>
    <div className="page-intro"><h1>Sản phẩm</h1><p>Quản lý thông tin sản phẩm, lượng nhập mỗi lần và mức tồn an toàn.</p></div>
    <Panel title="Danh sách sản phẩm" note="Chọn một sản phẩm để xem thông tin và chỉnh sửa cấu hình nhập hàng.">
      <div className="supply-filters">
        <label>Ngày xem trạng thái (UTC)<input type="date" value={day} onChange={(e) => { setDay(e.target.value); setPage(1); onContext?.({ origin: e.target.value }); }} /></label>
        <label>Ngừng nhập nội bộ<select value={status} disabled={!day || !supplyReady} onChange={(e) => {filter(setStatus,e.target.value);onContext?.({internalStatus:e.target.value});}}>
          <option value="">Tất cả trạng thái</option><option value="active">Đang cho nhập</option><option value="scheduled_stop">Đã lên lịch ngừng nhập</option><option value="stopped">Đã ngừng nhập nội bộ</option>
        </select></label>
        <label>Nhà mạng ngừng bán<select value={provider} disabled={!day || !tradeReady} onChange={e=>{filter(setProvider,e.target.value);onContext?.({providerStatus:e.target.value});}}><option value="">Tất cả trạng thái</option><option value="clear">Không bị chặn bán</option><option value="scheduled_stop">Sắp ngừng sản phẩm</option><option value="stopped">Đã ngừng mua và bán</option><option value="scheduled_resume">Chờ cung cấp trở lại</option></select></label>
      </div>
      <div className="product-filters">
        <label>Tìm sản phẩm<input type="search" value={search} placeholder="Nhập mã SKU" onChange={(e) => filter(setSearch, e.target.value)} /></label>
        <label>Kho sản phẩm<select value={warehouse} onChange={(e) => { filter(setWarehouse, e.target.value); onContext?.({ warehouseId: e.target.value, itemId: "" }); }}><option value="">Tất cả kho</option>{warehouses.data?.items.map((w) => <option key={String(w.id)} value={String(w.id)}>{warehouseName(w)}</option>)}</select></label>
        <label>Loại sản phẩm<select value={type} onChange={(e) => { filter(setType, e.target.value); onContext?.({ productType: e.target.value, itemId: "" }); }}><option value="">Tất cả loại</option><option>eSIM</option><option>physical_SIM</option></select></label>
      </div>
      <State loading={warehouses.loading} error={warehouses.error} />
      <State loading={data.loading} error={data.error} empty={!data.loading && !data.error && !data.data?.items.length} />
      {data.data && <><Table rows={data.data.items} onRow={onOpen} columns={[
        { key: "sku", label: "Mã sản phẩm", render: (v) => <strong>{String(v)}</strong> },
        { key: "product_type", label: "Loại" }, { key: "city", label: "Kho" }, { key: "carrier", label: "Nhà mạng" },
        { key: "internal_status", label: "Nhập nội bộ", render: (v,r) => internalLabel(v ?? r.supply_status) },
        { key: "provider_status", label: "Nhà mạng", render: (v,r) => r.trade_schema_ready?providerLabel(v):"Chức năng mới chưa bật" },
        { key: "policy", label: "Lượng nhập mỗi lần", render: (v) => (v as Row | null)?.fixed_order_qty == null ? "Chưa cấu hình" : fmt((v as Row).fixed_order_qty) },
        { key: "safety_days", label: "Tồn an toàn", render: (_, r) => { const p = r.policy as Row | null; return !p ? "Chưa cấu hình" : `${fmt(p.safety_days)} ngày`; } },
      ]} /><Pager page={page} total={data.data.total} onChange={setPage} /></>}
    </Panel>
  </>;
}

export function ProductDetail({ ctx, run, onNavigate, onWarehouse, onItem, onDate }: {
  ctx: Context; run?: Run; onDate?: (day: string) => void; onNavigate: (page: string) => void; onWarehouse: (row: Row) => void;
  onItem: (row: Row, page?: string, view?: PurchasingView) => void;
}) {
  const [revision, setRevision] = useState(0), [message, setMessage] = useState("");
  const [internalAction,setInternalAction]=useState<"stop"|"cancel_stop"|"resume">();
  const [day, setDay] = useState(ctx.origin);
  const notice = useRef<HTMLDivElement>(null);
  useEffect(() => setDay(ctx.origin), [ctx.origin, ctx.itemId]);
  const product = useResource<Row>(ctx.itemId ? `/products/${ctx.itemId}?${query({as_of_date:day})}` : null,true,revision);
  const ready = run?.status === "complete" && inventoryKinds.includes(run.kind) && !!ctx.origin;
  const stock = useResource<Page>(ready && product.data
    ? `/runs/${run.id}/inventory?${query({ item_id: product.data.id as number, date_from: ctx.origin, date_to: ctx.origin })}` : null);
  useEffect(() => {setMessage("");setInternalAction(undefined);}, [ctx.itemId]);
  useEffect(() => { if (message) notice.current?.focus(); }, [message, product.data?.id]);
  const row = String(product.data?.id)===ctx.itemId?product.data:undefined, policy = row?.policy as Row | null;
  return <>
    <nav className="warehouse-breadcrumb" aria-label="Đường dẫn sản phẩm"><button className="text-button" onClick={() => onNavigate("products")}>← Sản phẩm</button>{row && <><span>/</span><button className="text-button" onClick={() => onWarehouse(row)}>Kho {warehouseName(row)}</button><span>/</span><span aria-current="page">{String(row.sku)}</span></>}</nav>
    <State loading={product.loading} error={product.error} />
    {!ctx.itemId && <div className="notice" role="status">Chọn sản phẩm từ danh sách để xem thông tin.</div>}
    {row && <>
      <div className="page-heading"><div><h1>{String(row.sku)}</h1><p>{String(row.product_type)} · {warehouseName(row)} · {String(row.carrier)}</p></div></div>
      {message && <div className="notice success" role="status" ref={notice} tabIndex={-1}>{message}</div>}
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
      <Panel title="Quyền mua bán theo cấu hình mới nhất" note="Tách ngừng nhập nội bộ và hạn chế nhà mạng. Cấu hình nhập hàng không tự mở lại quyền.">
        <label className="supply-date">Ngày xem cấu hình UTC<input type="date" value={day} onChange={e=>{setDay(e.target.value);onDate?.(e.target.value);}} /></label>
        <TradeRights row={row} />
        <div className="form-actions"><button disabled={!day || row.trade_schema_ready!==true || row.internal_status==null} onClick={()=>setInternalAction(row.internal_status==="stopped"?"resume":row.internal_status==="scheduled_stop"?"cancel_stop":"stop")}>{row.internal_status==="stopped"?"Mở nhập lại nội bộ":row.internal_status==="scheduled_stop"?"Hủy lịch ngừng nhập":"Ngừng nhập nội bộ"}</button>
          <button onClick={()=>{const p=new URLSearchParams(location.search);Object.entries({day,sku:row.sku,type:row.product_type,supplier:row.supplier_id,warehouse:row.warehouse_id,country:row.destination_country,page:1,status:""}).forEach(([k,v])=>{if(v!=null)p.set("notice_"+k,String(v));});history.replaceState(history.state,"","?"+p+location.hash);onNavigate("provider-notices");}}>Quản lý thông báo nhà mạng</button></div>
        {Array.isArray(row.provider_notice_ids) && <div className="form-actions">{row.provider_notice_ids.map(id=><button className="text-button" key={String(id)} onClick={()=>onNavigate(`provider-notice:${id}`)}>Thông báo #{String(id)}</button>)}</div>}
        {row.trade_schema_ready!==true && <p className="notice">Chức năng mới chưa được bật. Kế hoạch và lịch sử cũ vẫn giữ nguyên.</p>}
      </Panel>
      {internalAction && <ProductSupplyForm product={row} day={day} run={run} action={internalAction} onClose={()=>setInternalAction(undefined)} onDate={value=>{setDay(value);onDate?.(value);}} onSaved={()=>{setInternalAction(undefined);setRevision(v=>v+1);setMessage("Đã lưu ngừng nhập nội bộ. Tạo kế hoạch mới để tính tác động; số liệu kế hoạch đang xem giữ nguyên.");}} />}
      {ready && <SellThrough runId={run.id} ctx={ctx} trade={isTradeRun(run)} />}
      {ready && <Panel title="Tình trạng tồn kho" note={`Số liệu trong kế hoạch tại ngày ${ctx.origin}. Lưu cấu hình không tính lại số liệu đã lưu.`}>
        <State loading={stock.loading} error={stock.error} empty={!stock.loading && !stock.error && !stock.data?.items.length} />
        {stock.data?.items[0] && <InventoryInformation focused={{ ...stock.data.items[0], display_city: row.city }} onItem={onItem} />}
      </Panel>}
    </>}
  </>;
}
