import { useState } from "react";
import { AccountMenu } from "../auth/SessionBoundary";
import { useResource } from "../hooks/useResource";
import { useDebounce } from "../hooks/useDebounce";
import { Table, type Column } from "../components/ui/Table";
import { Pager } from "../components/ui/Pager";
import { State } from "../components/ui/State";
import { WriteError } from "../operations/WriteError";
import { useOperationWrite, refreshOperations } from "../operations/useOperationWrite";
import { localTime, qty } from "../operations/types";
import { RequestDetail, statusBadge, type DealerRequest } from "./shared";
import type { Page } from "../types/api";

const TABS = [["home", "Tổng quan"], ["order", "Đặt hàng"], ["requests", "Yêu cầu của tôi"], ["stock", "Tồn của tôi"]] as const;
type Tab = typeof TABS[number][0];

export function DealerPortal() {
  const [tab, setTab] = useState<Tab>("home");
  return <div className="supplier-shell"><header className="topbar"><strong>SIGMA · Cổng đại lý</strong><AccountMenu /></header>
    <main className="supplier-workspace"><p className="eyebrow">KHÔNG GIAN ĐẠI LÝ</p><h1>{TABS.find(([key]) => key === tab)![1]}</h1>
      <nav className="supplier-tabs" aria-label="Nghiệp vụ đại lý">{TABS.map(([key, name]) =>
        <button key={key} aria-pressed={tab === key} onClick={() => setTab(key)}>{name}</button>)}</nav>
      {tab === "home" ? <Home onTab={setTab} /> : tab === "order" ? <OrderForm onDone={() => setTab("requests")} />
        : tab === "requests" ? <MyRequests /> : <MyStock />}
    </main></div>;
}

function Home({ onTab }: { onTab: (tab: Tab) => void }) {
  const waiting = useResource<Page>("/dealer/requests?status=submitted&page_size=1");
  const incoming = useResource<Page>("/dealer/requests?status=issued&page_size=1");
  const stock = useResource<Page>("/dealer/stock?page_size=1");
  const cards: [string, Page | undefined, boolean, Tab][] = [
    ["Yêu cầu chờ duyệt", waiting.data, waiting.loading, "requests"], ["Hàng đã xuất, chờ nhận", incoming.data, incoming.loading, "requests"],
    ["Mặt hàng đang có", stock.data, stock.loading, "stock"]];
  return <>
    <State error={waiting.error ?? incoming.error ?? stock.error} />
    <div className="ops-summary dashboard-summary" aria-busy={cards.some(([, , loading]) => loading)}>{cards.map(([label, data, loading, target]) =>
      <button key={label} onClick={() => onTab(target)}><span>{label}</span><strong>{loading ? <span className="skeleton-block" aria-hidden="true" /> : qty(data?.total)}</strong></button>)}</div>
    <p className="caption">Đặt hàng từ kho công ty, theo dõi trạng thái duyệt và xác nhận khi đã nhận hàng.</p>
    <button className="primary" onClick={() => onTab("order")}>Tạo yêu cầu lấy hàng</button>
  </>;
}

function OrderForm({ onDone }: { onDone: () => void }) {
  const [page, setPage] = useState(1), [search, setSearch] = useState(""), [note, setNote] = useState("");
  const [cart, setCart] = useState<Record<number, number>>({});
  const debounced = useDebounce(search);
  const products = useResource<Page>(`/dealer/products?page=${page}&page_size=25${debounced ? `&search=${encodeURIComponent(debounced)}` : ""}`, true);
  const write = useOperationWrite("/dealer");
  const lines = Object.entries(cart).filter(([, quantity]) => quantity > 0).map(([item, quantity]) => ({ item_id: Number(item), quantity }));
  const columns: Column[] = [
    { key: "sku", label: "SKU" }, { key: "name", label: "Sản phẩm" },
    { key: "product_type", label: "Loại", render: (value) => value === "physical_SIM" ? "SIM vật lý" : "eSIM" },
    { key: "available_qty", label: "Kho công ty còn", render: qty },
    { key: "item_id", label: "Số lượng đặt", render: (value, row) => <input type="number" min={0} step={1} aria-label={`Số lượng ${row.sku}`}
      value={cart[Number(value)] ?? ""} onChange={(event) => setCart((current) => ({ ...current, [Number(value)]: Math.max(0, Math.floor(Number(event.target.value) || 0)) }))} /> },
  ];
  async function submit() {
    if (await write.send("/requests", { note, lines })) { setCart({}); setNote(""); refreshOperations(); onDone(); }
  }
  return <section className="panel ops-list-panel">
    <div className="ops-filters"><label>Tìm sản phẩm<input value={search} maxLength={120} placeholder="Mã hoặc tên sản phẩm" onChange={(event) => { setSearch(event.target.value); setPage(1); }} /></label></div>
    <State error={products.error} />
    {!products.error && <><Table rows={products.data?.items ?? []} loading={products.loading} columns={columns} label="Sản phẩm có thể đặt" emptyMessage="Chưa có sản phẩm đang kinh doanh." />
      <Pager page={page} total={products.data?.total ?? 0} pageSize={25} loading={products.loading} onChange={setPage} /></>}
    <WriteError error={write.error} />
    <label>Ghi chú cho kho<textarea value={note} maxLength={1000} rows={2} onChange={(event) => setNote(event.target.value)} /></label>
    <div className="dialog-form-actions"><span className="caption">{lines.length} sản phẩm · {qty(lines.reduce((sum, line) => sum + line.quantity, 0))} đơn vị</span>
      <button className="primary" disabled={!lines.length || write.busy} onClick={() => void submit()}>{write.busy ? "Đang gửi…" : "Gửi yêu cầu"}</button></div>
  </section>;
}

function MyRequests() {
  const [page, setPage] = useState(1), [open, setOpen] = useState("");
  const result = useResource<Page>(`/dealer/requests?page=${page}&page_size=25`, true);
  const write = useOperationWrite("/dealer/requests");
  async function act(request: DealerRequest, action: "cancel" | "receive") {
    if (await write.send(`/${request.id}/${action}`, { expected_version: request.version })) { refreshOperations(); setOpen(""); }
  }
  const columns: Column[] = [
    { key: "number", label: "Yêu cầu", render: (value, row) => <button className="text-button" onClick={() => setOpen(String(row.id))}>{String(value)}</button> },
    { key: "status", label: "Trạng thái", render: statusBadge }, { key: "quantity", label: "Tổng số lượng", render: qty }, { key: "created_at", label: "Tạo lúc", render: localTime },
  ];
  return <section className="panel ops-list-panel">
    <State error={result.error} />
    {!result.error && <><Table rows={result.data?.items ?? []} loading={result.loading} columns={columns} label="Yêu cầu của tôi" emptyMessage="Bạn chưa gửi yêu cầu nào." />
      <Pager page={page} total={result.data?.total ?? 0} pageSize={25} loading={result.loading} onChange={setPage} /></>}
    {open && <RequestDetail path={`/dealer/requests/${open}`} onClose={() => setOpen("")} busy={write.busy} error={write.error} actions={(request) => <>
      {request.status === "submitted" && <button onClick={() => void act(request, "cancel")}>Hủy yêu cầu</button>}
      {request.status === "issued" && <button className="primary" onClick={() => void act(request, "receive")}>Xác nhận đã nhận hàng</button>}
    </>} />}
  </section>;
}

function MyStock() {
  const [page, setPage] = useState(1);
  const result = useResource<Page>(`/dealer/stock?page=${page}&page_size=25`, true);
  return <section className="panel ops-list-panel">
    <p className="caption">Tổng số đã nhận từ công ty. Hệ thống chưa ghi nhận số đại lý đã bán ra.</p>
    <State error={result.error} />
    {!result.error && <><Table rows={result.data?.items ?? []} loading={result.loading} label="Tồn của tôi" emptyMessage="Chưa nhận hàng lần nào."
      columns={[{ key: "sku", label: "SKU" }, { key: "name", label: "Sản phẩm" }, { key: "received_qty", label: "Đã nhận", render: qty }]} />
      <Pager page={page} total={result.data?.total ?? 0} pageSize={25} loading={result.loading} onChange={setPage} /></>}
  </section>;
}
