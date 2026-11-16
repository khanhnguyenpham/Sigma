import { useState, type FormEvent, type ReactNode } from "react";
import { useResource } from "../hooks/useResource";
import { apiAllPages } from "../services/http";
import { Table, type Column } from "../components/ui/Table";
import { Pager } from "../components/ui/Pager";
import { State } from "../components/ui/State";
import { Dialog } from "../components/ui/Dialog";
import { WriteError } from "../operations/WriteError";
import { useOperationWrite, refreshOperations } from "../operations/useOperationWrite";
import { localTime, qty, type OpsSummary, type Warehouse } from "../operations/types";
import { REQUEST_STATUS, RequestDetail, statusBadge, type DealerRequest } from "../dealers/shared";
import type { Page } from "../types/api";

interface Dealer { id: number; code: string; name: string; contact: string; active: boolean; version: number; [key: string]: unknown }

function Heading({ title, caption, action }: { title: string; caption: string; action?: ReactNode }) {
  return <div className="ops-section-heading"><div><p className="eyebrow">ĐẠI LÝ</p><h1>{title}</h1><p className="caption">{caption}</p></div>{action}</div>;
}

export function DealersPage() {
  const [page, setPage] = useState(1);
  const [editor, setEditor] = useState<Dealer | "new">();
  const result = useResource<Page<Dealer>>(`/dealers?page=${page}&page_size=25`, true);
  const columns: Column[] = [
    { key: "code", label: "Mã đại lý" }, { key: "name", label: "Tên đại lý" }, { key: "contact", label: "Liên hệ" },
    { key: "active", label: "Trạng thái", render: (value) => value ? "Hoạt động" : "Ngừng hoạt động" },
    { key: "id", label: "Thao tác", render: (_, row) => <button onClick={() => setEditor(row as Dealer)}>Chỉnh sửa</button> },
  ];
  return <div className="operations-workspace">
    <Heading title="Danh sách đại lý" caption="Tạo đại lý trước, sau đó cấp tài khoản đại lý trong mục Tài khoản."
      action={<button className="primary" onClick={() => setEditor("new")}>Thêm đại lý</button>} />
    <section className="panel ops-list-panel">
      <State error={result.error} />
      {!result.error && <><Table rows={result.data?.items ?? []} loading={result.loading} columns={columns} label="Danh sách đại lý" emptyMessage="Chưa có đại lý nào." />
        <Pager page={page} total={result.data?.total ?? 0} pageSize={25} loading={result.loading} onChange={setPage} /></>}
    </section>
    {editor && <DealerEditor row={editor === "new" ? undefined : editor} onClose={() => setEditor(undefined)} />}
  </div>;
}

function DealerEditor({ row, onClose }: { row?: Dealer; onClose: () => void }) {
  const write = useOperationWrite("/dealers");
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const fields = new FormData(event.currentTarget);
    const body = { name: fields.get("name"), contact: fields.get("contact"),
      ...(row ? { active: fields.get("active") === "true", expected_version: row.version } : { code: fields.get("code") }) };
    if (await write.send(row ? `/${row.id}` : "", body, row ? "PATCH" : "POST")) { refreshOperations(); onClose(); }
  }
  return <Dialog title={row ? `Cập nhật ${row.code}` : "Thêm đại lý"} onClose={onClose} busy={write.busy} className="operations-form-dialog">
    <form onSubmit={(event) => void save(event)}><fieldset disabled={write.busy}><div className="operations-form-fields">
      <WriteError error={write.error} />
      {!row && <label>Mã đại lý<input name="code" required maxLength={40} pattern="[A-Za-z0-9][A-Za-z0-9_\-]*" placeholder="VD: DL-HN-01" /></label>}
      <label>Tên đại lý<input name="name" required maxLength={120} defaultValue={row?.name ?? ""} /></label>
      <label>Liên hệ<input name="contact" maxLength={200} defaultValue={row?.contact ?? ""} placeholder="Số điện thoại hoặc email" /></label>
      {row && <label>Trạng thái<select name="active" defaultValue={String(row.active)}><option value="true">Hoạt động</option><option value="false">Ngừng hoạt động</option></select></label>}
    </div><div className="dialog-form-actions"><button type="button" onClick={onClose}>Hủy</button><button className="primary" type="submit">{write.busy ? "Đang lưu…" : "Lưu"}</button></div></fieldset></form>
  </Dialog>;
}

export function DealerRequestsPage() {
  const [page, setPage] = useState(1), [status, setStatus] = useState("submitted"), [open, setOpen] = useState("");
  const result = useResource<Page>(`/dealers/requests?page=${page}&page_size=25${status ? `&status=${status}` : ""}`, true);
  const columns: Column[] = [
    { key: "number", label: "Yêu cầu", render: (value, row) => <button className="text-button" onClick={() => setOpen(String(row.id))}>{String(value)}</button> },
    { key: "dealer_name", label: "Đại lý" }, { key: "status", label: "Trạng thái", render: statusBadge },
    { key: "line_count", label: "Số dòng" }, { key: "quantity", label: "Tổng số lượng", render: qty }, { key: "created_at", label: "Tạo lúc", render: localTime },
  ];
  return <div className="operations-workspace">
    <Heading title="Yêu cầu lấy hàng" caption="Duyệt yêu cầu của đại lý, sau đó chọn kho để xuất hàng." />
    <section className="panel ops-list-panel">
      <div className="ops-filters"><label>Trạng thái<select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}>
        <option value="">Tất cả</option>{Object.entries(REQUEST_STATUS).map(([key, name]) => <option key={key} value={key}>{name}</option>)}</select></label></div>
      <State error={result.error} />
      {!result.error && <><Table rows={result.data?.items ?? []} loading={result.loading} columns={columns} label="Yêu cầu lấy hàng" emptyMessage="Không có yêu cầu phù hợp." />
        <Pager page={page} total={result.data?.total ?? 0} pageSize={25} loading={result.loading} onChange={setPage} /></>}
    </section>
    {open && <AdminRequest id={open} onClose={() => setOpen("")} />}
  </div>;
}

function AdminRequest({ id, onClose }: { id: string; onClose: () => void }) {
  const write = useOperationWrite("/dealers/requests");
  const [mode, setMode] = useState<"" | "reject" | "issue">("");
  const [reason, setReason] = useState(""), [warehouse, setWarehouse] = useState("");
  const warehouses = useResource<Page<Warehouse>>(mode === "issue" ? "/operations/warehouses?active=true&page_size=100" : null, false, 0, apiAllPages);
  const summary = useResource<OpsSummary>(mode === "issue" ? "/operations/summary" : null);
  async function act(request: DealerRequest, action: string, extra: Record<string, unknown> = {}) {
    if (await write.send(`/${request.id}/${action}`, { expected_version: request.version, ...extra })) { refreshOperations(); onClose(); }
  }
  return <RequestDetail path={`/dealers/requests/${id}`} onClose={onClose} busy={write.busy} error={write.error} actions={(request) => {
    if (mode === "reject") return <>
      <label className="dialog-inline-field">Lý do từ chối<input value={reason} maxLength={1000} onChange={(event) => setReason(event.target.value)} /></label>
      <button type="button" onClick={() => setMode("")}>Quay lại</button>
      <button className="primary" disabled={!reason.trim()} onClick={() => void act(request, "reject", { reason })}>Xác nhận từ chối</button></>;
    if (mode === "issue") return <>
      <label className="dialog-inline-field">Xuất từ kho<select value={warehouse} onChange={(event) => setWarehouse(event.target.value)}>
        <option value="">{warehouses.loading ? "Đang tải kho…" : "Chọn kho"}</option>{warehouses.data?.items.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
      <button type="button" onClick={() => setMode("")}>Quay lại</button>
      <button className="primary" disabled={!warehouse || !summary.data} onClick={() => void act(request, "issue",
        { warehouse_id: Number(warehouse), occurred_on: summary.data!.business_date })}>Xuất kho</button></>;
    return <>
      {["submitted", "approved"].includes(request.status) && <button onClick={() => setMode("reject")}>Từ chối</button>}
      {request.status === "submitted" && <button className="primary" onClick={() => void act(request, "approve")}>Duyệt</button>}
      {request.status === "approved" && <button className="primary" onClick={() => setMode("issue")}>Xuất kho</button>}
    </>;
  }} />;
}
