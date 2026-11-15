import { useState } from "react";
import { AccountMenu } from "./SessionBoundary";
import { useResource } from "../hooks/useResource";
import type { Page } from "../types/api";
import { Table } from "../components/ui/Table";
import { State } from "../components/ui/State";
import { Pager } from "../components/ui/Pager";
import { Dialog } from "../components/ui/Dialog";
import { ORDER_STATUS, qty } from "../operations/types";

export function SupplierPortal() {
  const [tab, setTab] = useState<"products" | "orders">("orders");
  const [page, setPage] = useState(1);
  const result = useResource<Page>(`/supplier/${tab === "products" ? "operational-products" : "orders"}?page=${page}&page_size=25`);
  const [orderId, setOrderId] = useState("");
  const detail = useResource<import("../operations/types").Order>(orderId ? `/supplier/orders/${orderId}` : null);
  return <div className="supplier-shell"><header className="topbar"><strong>SIGMA · Cổng nhà cung cấp</strong><AccountMenu /></header>
    <main className="supplier-workspace"><p className="eyebrow">KHÔNG GIAN ĐỐI TÁC</p><h1>Đơn nhập & sản phẩm</h1>
      <p>Chỉ hiển thị dữ liệu thuộc nhà cung cấp của bạn.</p>
      <nav className="supplier-tabs" aria-label="Nghiệp vụ nhà cung cấp">{([['orders', 'Đơn nhập'], ['products', 'Sản phẩm']] as const).map(([key, name]) =>
        <button key={key} aria-pressed={tab === key} onClick={() => { setTab(key); setPage(1); setOrderId(""); }}>{name}</button>)}</nav>
      <section className="panel"><h2>{tab === "products" ? "Danh sách sản phẩm" : "Đơn nhập hàng"}</h2>
        <State error={result.error} />
        {!result.error && <><Table loading={result.loading} rows={result.data?.items ?? []} columns={tab === "products" ? [
          { key: "sku", label: "Mã sản phẩm" }, { key: "product_type", label: "Loại" }, { key: "destination_country", label: "Quốc gia" },
          { key: "carrier", label: "Nhà mạng" }, { key: "name", label: "Tên sản phẩm" },
        ] : [
          { key: "number", label: "Đơn nhập", render: (value, row) => <button className="text-button" onClick={() => setOrderId(String(row.id))}>{String(value)}</button> },
          { key: "ordered_on", label: "Ngày đặt" }, { key: "eta", label: "Ngày về dự kiến" },
          { key: "ordered_qty", label: "Số lượng" }, { key: "received_qty", label: "Đã nhận" },
          { key: "status", label: "Trạng thái", render: (value) => ORDER_STATUS[String(value)] ?? "Không có" },
        ]} /><Pager page={page} total={result.data?.total ?? 0} pageSize={25} onChange={setPage} /></>}
      </section>
      {orderId && <Dialog title={detail.data?.number ?? "Chi tiết đơn nhập"} onClose={() => setOrderId("")} className="operations-form-dialog wide"><div className="operations-form-fields"><State loading={detail.loading} error={detail.error} />{detail.data && !detail.error && <><p>Dự kiến nhận: {detail.data.eta} · {ORDER_STATUS[detail.data.status]}</p><Table rows={detail.data.lines} columns={[{ key: "sku", label: "SKU" }, { key: "warehouse", label: "Kho nhận" }, { key: "ordered_qty", label: "Đã đặt", render: qty }, { key: "received_qty", label: "Đã nhận", render: qty }, { key: "remaining_qty", label: "Chưa nhận", render: qty }]} /></>}</div></Dialog>}
    </main></div>;
}
