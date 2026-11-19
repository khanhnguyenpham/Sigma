import { useEffect, useState } from "react";
import { AccountMenu } from "../auth/SessionBoundary";
import { useResource } from "../hooks/useResource";
import { useDebounce } from "../hooks/useDebounce";
import { query } from "../utils/url";
import { Card } from "../components/ui/Card";
import { Icon } from "../components/ui/Icon";
import { Table, type Column } from "../components/ui/Table";
import { Pager } from "../components/ui/Pager";
import { State } from "../components/ui/State";
import { WriteError } from "../operations/WriteError";
import { FilterBar, PRODUCT_TYPES } from "../operations/Filters";
import { productType } from "../operations/productColumns";
import { useOperationWrite, refreshOperations } from "../operations/useOperationWrite";
import { localTime, qty } from "../operations/types";
import { REQUEST_STATUS, RequestDetail, statusBadge, type DealerRequest } from "./shared";
import type { Page, Row } from "../types/api";

const TABS = [["home", "Tổng quan"], ["order", "Đặt hàng"], ["requests", "Yêu cầu của tôi"], ["stock", "Tồn của tôi"]] as const;
type Tab = typeof TABS[number][0];
// What the dealer should expect next, shown on each request.
const NEXT_STEP: Record<string, string> = {
  submitted: "Công ty đang xem xét. Bạn còn có thể hủy yêu cầu trước khi được duyệt.",
  approved: "Đã duyệt. Kho sẽ xuất hàng; khi xuất xong bạn xác nhận đã nhận tại đây.",
  issued: "Kho đã xuất hàng. Kiểm hàng rồi bấm Xác nhận đã nhận hàng.",
  received: "Hoàn tất. Số lượng đã cộng vào Tồn của tôi.",
  rejected: "Công ty đã từ chối. Xem lý do bên trên và gửi yêu cầu mới nếu cần.",
  cancelled: "Bạn đã hủy yêu cầu này.",
};
// Prefixed so a dealer hash never names an admin page if someone else signs in on the same tab.
const tabFromHash = (): Tab => TABS.find(([key]) => `#dealer-${key}` === location.hash)?.[0] ?? "home";

export function DealerPortal() {
  const [tab, setTabState] = useState<Tab>(tabFromHash);
  const [notice, setNotice] = useState("");
  // The tab lives in the URL hash so reload and the back button keep the dealer's place.
  useEffect(() => { const sync = () => setTabState(tabFromHash()); addEventListener("hashchange", sync); return () => removeEventListener("hashchange", sync); }, []);
  function setTab(next: Tab) { if (next !== tab) history.pushState(null, "", `#dealer-${next}`); setTabState(next); setNotice(""); }
  return <div className="supplier-shell"><header className="topbar"><strong>SIGMA · Cổng đại lý</strong><AccountMenu /></header>
    <main className="supplier-workspace"><p className="eyebrow">KHÔNG GIAN ĐẠI LÝ</p><h1>{TABS.find(([key]) => key === tab)![1]}</h1>
      <nav className="supplier-tabs" aria-label="Nghiệp vụ đại lý">{TABS.map(([key, name]) =>
        <button key={key} aria-pressed={tab === key} onClick={() => setTab(key)}>{name}</button>)}</nav>
      {notice && <p className="notice success" role="status">{notice}</p>}
      {tab === "home" ? <Home onTab={setTab} /> : tab === "order" ? <OrderForm onDone={(number) => { setTab("requests"); setNotice(`Đã gửi yêu cầu ${number}. Công ty sẽ duyệt và xuất hàng; theo dõi trạng thái bên dưới.`); }} />
        : tab === "requests" ? <MyRequests /> : <MyStock onOrder={() => setTab("order")} />}
    </main></div>;
}

function Home({ onTab }: { onTab: (tab: Tab) => void }) {
  const waiting = useResource<Page>("/dealer/requests?status=submitted&page_size=1");
  const approved = useResource<Page>("/dealer/requests?status=approved&page_size=1");
  const incoming = useResource<Page>("/dealer/requests?status=issued&page_size=1");
  const stock = useResource<Page>("/dealer/stock?page_size=1");
  const recent = useResource<Page>("/dealer/requests?page_size=5");
  const [open, setOpen] = useState("");
  const cards: [string, Page | undefined, boolean, Tab, string, string, string][] = [
    ["Yêu cầu chờ duyệt", waiting.data, waiting.loading, "requests", "clock", "orange", "Công ty chưa xử lý"],
    ["Đã duyệt, chờ xuất", approved.data, approved.loading, "requests", "check", "", "Kho đang chuẩn bị hàng"],
    ["Hàng đã xuất, chờ nhận", incoming.data, incoming.loading, "requests", "truck", "teal", "Cần bạn xác nhận khi nhận"],
    ["Mặt hàng đã nhận", stock.data, stock.loading, "stock", "box", "", "Tổng từ các lần nhận"]];
  return <>
    <State error={waiting.error ?? approved.error ?? incoming.error ?? stock.error} />
    <div className="stats dashboard-summary dealer-summary">{cards.map(([label, data, loading, target, icon, tone, note]) =>
      <button key={label} className="stat-button" onClick={() => onTab(target)} aria-label={`${label}: ${loading ? "đang tải" : qty(data?.total)}`}>
        <Card label={label} value={loading ? "—" : qty(data?.total)} note={note} icon={icon} tone={Number(data?.total) > 0 ? tone : ""} /></button>)}</div>
    <section className="panel ops-list-panel">
      <div className="panel-title"><div><h2>Yêu cầu gần đây</h2><p>Đặt hàng từ kho công ty, theo dõi duyệt và xác nhận khi đã nhận hàng.</p></div>
        <div className="ops-actions"><button className="text-button" onClick={() => onTab("requests")}>Xem tất cả</button>
          <button className="primary" onClick={() => onTab("order")}><Icon name="plus" size={16} /> Tạo yêu cầu lấy hàng</button></div></div>
      <State error={recent.error} />
      {!recent.error && <Table rows={recent.data?.items ?? []} loading={recent.loading} label="Yêu cầu gần đây" onRow={(row) => setOpen(String(row.id))}
        emptyMessage="Bạn chưa gửi yêu cầu nào. Bấm Tạo yêu cầu lấy hàng để bắt đầu." columns={REQUEST_COLUMNS} />}
    </section>
    {open && <RequestActions id={open} onClose={() => setOpen("")} />}
  </>;
}

const REQUEST_COLUMNS: Column[] = [
  { key: "number", label: "Yêu cầu", render: (value) => <span className="link-text">{String(value)}</span> },
  { key: "status", label: "Trạng thái", render: statusBadge }, { key: "line_count", label: "Số sản phẩm", render: qty },
  { key: "quantity", label: "Tổng số lượng", render: qty }, { key: "created_at", label: "Tạo lúc", render: localTime },
];

interface CartLine { quantity: number; name: string; sku: string; available: number }

function OrderForm({ onDone }: { onDone: (number: string) => void }) {
  const [page, setPage] = useState(1), [note, setNote] = useState("");
  const [filters, setFilters] = useState<Record<string, string>>({ in_stock: "true" });
  const [cart, setCart] = useState<Record<number, CartLine>>({});
  const search = useDebounce(filters.search ?? "");
  const products = useResource<Page>(`/dealer/products?${query({ page, page_size: 25, ...filters, search })}`, true);
  const options = useResource<{ countries: string[]; carriers: string[] }>("/dealer/product-filters");
  const write = useOperationWrite("/dealer");
  const lines = Object.entries(cart).map(([item, line]) => ({ item_id: Number(item), ...line }));
  const over = lines.filter((line) => line.quantity > line.available);
  function setQuantity(row: Row, raw: string) {
    const quantity = Math.max(0, Math.floor(Number(raw) || 0)), id = Number(row.item_id);
    setCart((current) => {
      const { [id]: _, ...rest } = current;
      return quantity ? { ...rest, [id]: { quantity, name: String(row.name), sku: String(row.sku), available: Number(row.available_qty) } } : rest;
    });
  }
  const columns: Column[] = [
    { key: "name", label: "Sản phẩm", render: (value, row) => <span><strong>{String(value)}</strong><small className="cell-subtitle">{String(row.sku)}</small></span> },
    { key: "product_type", label: "Loại", render: productType }, { key: "destination_country", label: "Quốc gia" },
    { key: "available_qty", label: "Kho công ty còn", render: (value) => Number(value) > 0 ? qty(value) : <span className="ops-status cancelled">Hết hàng</span> },
    { key: "item_id", label: "Số lượng đặt", render: (value, row) => {
      const line = cart[Number(value)];
      return <span className="dealer-qty"><input type="number" min={0} step={1} aria-label={`Số lượng ${String(row.name)}`}
        aria-invalid={line && line.quantity > Number(row.available_qty) ? true : undefined}
        value={line?.quantity ?? ""} onChange={(event) => setQuantity(row, event.target.value)} />
        {line && line.quantity > Number(row.available_qty) && <small className="field-warning">Vượt số kho còn</small>}</span>;
    } },
  ];
  async function submit() {
    const sent = await write.send<DealerRequest>("/requests", { note, lines: lines.map(({ item_id, quantity }) => ({ item_id, quantity })) });
    if (sent) { setCart({}); setNote(""); refreshOperations(); onDone(sent.number); }
  }
  const units = lines.reduce((sum, line) => sum + line.quantity, 0);
  return <>
    <section className="panel ops-list-panel">
      <FilterBar values={filters} onChange={(key, value) => { setFilters((current) => ({ ...current, [key]: value })); setPage(1); }}
        onReset={() => { setFilters({}); setPage(1); }} fields={[
          { key: "search", label: "Tìm sản phẩm", type: "search", placeholder: "Mã hoặc tên sản phẩm" },
          { key: "in_stock", label: "Tình trạng", type: "select", options: [["true", "Chỉ hàng còn"]], all: "Tất cả sản phẩm" },
          { key: "country", label: "Quốc gia", type: "select", options: (options.data?.countries ?? []).map((name) => [name, name] as const), all: "Tất cả quốc gia" },
          { key: "carrier", label: "Nhà mạng", type: "select", options: (options.data?.carriers ?? []).map((name) => [name, name] as const), all: "Tất cả nhà mạng" },
          { key: "product_type", label: "Loại", type: "select", options: PRODUCT_TYPES },
        ]} />
      <State error={products.error} />
      {!products.error && <><Table rows={products.data?.items ?? []} loading={products.loading} columns={columns} stickyFirstColumn label="Sản phẩm có thể đặt"
        emptyMessage={filters.in_stock ? "Không có sản phẩm còn hàng phù hợp. Chọn Tất cả sản phẩm để xem cả hàng đã hết." : "Không có sản phẩm phù hợp."} />
        <Pager page={page} total={products.data?.total ?? 0} pageSize={25} loading={products.loading} onChange={setPage} /></>}
    </section>
    {lines.length > 0 && <section className="panel dealer-cart" aria-label="Giỏ yêu cầu" id="dealer-cart">
      <div className="panel-title"><div><h2>Giỏ yêu cầu</h2><p>Kiểm lại trước khi gửi. Số lượng giữ nguyên khi bạn đổi trang hoặc bộ lọc.</p></div>
        <button className="text-button" onClick={() => setCart({})}>Xóa giỏ</button></div>
      <Table rows={lines as unknown as Row[]} label="Sản phẩm trong giỏ" columns={[
        { key: "name", label: "Sản phẩm", render: (value, row) => <span><strong>{String(value)}</strong><small className="cell-subtitle">{String(row.sku)}</small></span> },
        { key: "available", label: "Kho công ty còn", render: qty },
        { key: "quantity", label: "Số lượng", render: (value, row) => <span className={Number(value) > Number(row.available) ? "field-warning" : undefined}>{qty(value)}</span> },
        { key: "item_id", label: "", render: (value) => <button className="text-button" aria-label={`Bỏ khỏi giỏ`} onClick={() => setCart(({ [Number(value)]: _, ...rest }) => rest)}>Bỏ</button> },
      ]} />
      {over.length > 0 && <p className="notice">{over.length} sản phẩm đặt nhiều hơn số kho công ty đang còn. Bạn vẫn gửi được; công ty có thể chỉ duyệt khi có đủ hàng.</p>}
      <label>Ghi chú cho kho<textarea value={note} maxLength={1000} rows={2} placeholder="VD: cần trước thứ Sáu, giao kèm hóa đơn…" onChange={(event) => setNote(event.target.value)} /></label>
      <WriteError error={write.error} />
    </section>}
    <div className="dealer-cart-bar" role="region" aria-label="Tóm tắt giỏ yêu cầu">
      <span><strong>{lines.length}</strong> sản phẩm · <strong>{qty(units)}</strong> đơn vị{over.length > 0 && <span className="field-warning"> · {over.length} vượt tồn</span>}</span>
      <div className="ops-actions">{lines.length > 0 && <a className="text-button" href="#dealer-cart" onClick={(event) => { event.preventDefault(); document.getElementById("dealer-cart")?.scrollIntoView({ behavior: "smooth" }); }}>Xem giỏ</a>}
        <button className="primary" disabled={!lines.length || write.busy} onClick={() => void submit()}>{write.busy ? "Đang gửi…" : "Gửi yêu cầu"}</button></div>
    </div>
  </>;
}

function RequestActions({ id, onClose }: { id: string; onClose: () => void }) {
  const write = useOperationWrite("/dealer/requests");
  const [confirming, setConfirming] = useState(false);
  async function act(request: DealerRequest, action: "cancel" | "receive") {
    if (await write.send(`/${request.id}/${action}`, { expected_version: request.version })) { refreshOperations(); onClose(); }
  }
  return <RequestDetail path={`/dealer/requests/${id}`} onClose={onClose} busy={write.busy} error={write.error} actions={(request) => <>
    <span className="caption request-next-step">{NEXT_STEP[request.status]}</span>
    {request.status === "submitted" && (confirming ? <>
      <span className="caption">Hủy yêu cầu này?</span>
      <button onClick={() => setConfirming(false)}>Không</button>
      <button className="danger" onClick={() => void act(request, "cancel")}>Xác nhận hủy</button></>
      : <button onClick={() => setConfirming(true)}>Hủy yêu cầu</button>)}
    {request.status === "issued" && <button className="primary" onClick={() => void act(request, "receive")}>Xác nhận đã nhận hàng</button>}
  </>} />;
}

function MyRequests() {
  const [page, setPage] = useState(1), [open, setOpen] = useState(""), [filters, setFilters] = useState<Record<string, string>>({});
  const result = useResource<Page>(`/dealer/requests?${query({ page, page_size: 25, ...filters })}`, true);
  const columns: Column[] = [{ ...REQUEST_COLUMNS[0], render: (value, row) => <button className="text-button" onClick={(event) => { event.stopPropagation(); setOpen(String(row.id)); }}>{String(value)}</button> }, ...REQUEST_COLUMNS.slice(1)];
  return <section className="panel ops-list-panel">
    <FilterBar values={filters} onChange={(key, value) => { setFilters((current) => ({ ...current, [key]: value })); setPage(1); }}
      onReset={() => { setFilters({}); setPage(1); }} fields={[{ key: "status", label: "Trạng thái", type: "select", options: Object.entries(REQUEST_STATUS) }]} />
    <State error={result.error} />
    {!result.error && <><Table rows={result.data?.items ?? []} loading={result.loading} columns={columns} onRow={(row) => setOpen(String(row.id))} label="Yêu cầu của tôi"
      emptyMessage={filters.status ? "Không có yêu cầu ở trạng thái này." : "Bạn chưa gửi yêu cầu nào."} />
      <Pager page={page} total={result.data?.total ?? 0} pageSize={25} loading={result.loading} onChange={setPage} /></>}
    {open && <RequestActions id={open} onClose={() => setOpen("")} />}
  </section>;
}

function MyStock({ onOrder }: { onOrder: () => void }) {
  const [page, setPage] = useState(1);
  const result = useResource<Page>(`/dealer/stock?page=${page}&page_size=25`, true);
  return <section className="panel ops-list-panel">
    <div className="panel-title"><div><h2>Hàng đã nhận</h2><p>Tổng số đã nhận từ công ty. Hệ thống chưa ghi nhận số đại lý đã bán ra.</p></div>
      <button onClick={onOrder}>Đặt thêm hàng</button></div>
    <State error={result.error} />
    {!result.error && <><Table rows={result.data?.items ?? []} loading={result.loading} label="Tồn của tôi" emptyMessage="Chưa nhận hàng lần nào. Hàng sẽ hiện ở đây sau khi bạn xác nhận đã nhận."
      columns={[{ key: "name", label: "Sản phẩm", render: (value, row) => <span><strong>{String(value)}</strong><small className="cell-subtitle">{String(row.sku)}</small></span> },
        { key: "received_qty", label: "Đã nhận", render: qty }]} />
      <Pager page={page} total={result.data?.total ?? 0} pageSize={25} loading={result.loading} onChange={setPage} /></>}
  </section>;
}
