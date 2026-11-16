import { useEffect, useRef, useState, type FormEvent } from "react";
import type { Page } from "../types/api";
import { useResource } from "../hooks/useResource";
import { api } from "../services/http";
import { Table } from "../components/ui/Table";
import { State } from "../components/ui/State";
import { Pager } from "../components/ui/Pager";
import type { User } from "./SessionBoundary";

export function UserManagement({ currentId, onClose }: { currentId: number; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [page, setPage] = useState(1);
  const [role, setRole] = useState("dealer");
  const [error, setError] = useState<Error>();
  const [busy, setBusy] = useState(false);
  const users = useResource<Page<User>>(`/auth/users?page=${page}&page_size=25`, true);
  const dealers = useResource<Page>("/dealers?active=true&page_size=100");
  useEffect(() => { dialog.current?.showModal(); }, []);
  function refresh() { window.dispatchEvent(new Event("sigma:refresh")); }
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const fields = new FormData(form);
    setBusy(true); setError(undefined);
    try {
      await api("/auth/users", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
        username: String(fields.get("username")).trim().toLowerCase(), display_name: fields.get("display_name"), password: fields.get("password"), role,
        dealer_id: role === "dealer" ? Number(fields.get("dealer_id")) : null,
      }) });
      form.reset(); refresh();
    } catch (err) { setError(err as Error); } finally { setBusy(false); }
  }
  async function toggle(user: User) {
    setBusy(true); setError(undefined);
    try { await api(`/auth/users/${user.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ active: !user.active }) }); refresh(); }
    catch (err) { setError(err as Error); } finally { setBusy(false); }
  }
  return <dialog className="accounts-dialog" ref={dialog} onCancel={onClose} aria-labelledby="accounts-title">
    <div className="panel-title"><h2 id="accounts-title">Quản lý tài khoản</h2><button onClick={onClose}>Đóng</button></div>
    <p>Admin quản lý toàn hệ thống. Mỗi tài khoản đại lý chỉ thấy yêu cầu và tồn của một đại lý. Tài khoản nhà cung cấp cũ đã ngừng sử dụng.</p>
    <State error={error ?? users.error ?? dealers.error} />
    {!users.error && <><Table loading={users.loading} rows={users.data?.items.map((user) => ({ ...user })) ?? []} columns={[
      { key: "display_name", label: "Họ tên" }, { key: "username", label: "Đăng nhập" },
      { key: "role", label: "Quyền", render: (value) => value === "admin" ? "Quản trị viên" : value === "dealer" ? "Đại lý" : "Nhà cung cấp (đã ngừng)" },
      { key: "dealer_id", label: "Đại lý", render: (value) => dealers.data?.items.find((row) => row.id === value)?.name as string ?? (value ? `#${value}` : "") },
      { key: "active", label: "Trạng thái", render: (value) => value ? "Hoạt động" : "Đã khóa" },
      { key: "id", label: "Thao tác", render: (_value, row) => <button disabled={busy || row.id === currentId || (row.role === "supplier" && !row.active)} onClick={() => void toggle(row as unknown as User)}>{row.active ? "Khóa" : "Mở khóa"}</button> },
    ]} /><Pager page={page} total={users.data?.total ?? 0} pageSize={25} loading={users.loading} onChange={setPage} /></>}
    <h3>Tạo tài khoản</h3><form className="account-form" onSubmit={(event) => void create(event)} aria-busy={busy}>
      <fieldset disabled={busy}><label>Tên hiển thị<input name="display_name" required maxLength={100} /></label>
        <label>Tên đăng nhập<input name="username" required minLength={3} maxLength={64} pattern="[a-z0-9][a-z0-9._\-]{2,63}" autoComplete="off" /></label>
        <label>Mật khẩu<input name="password" type="password" required minLength={12} maxLength={128} autoComplete="new-password" /></label>
        <label>Quyền<select aria-label="Quyền tài khoản" value={role} onChange={(e) => setRole(e.target.value)}><option value="dealer">Đại lý</option><option value="admin">Quản trị viên</option></select></label>
        {role === "dealer" && <label>Đại lý<select aria-label="Đại lý của tài khoản" name="dealer_id" required defaultValue=""><option value="" disabled>Chọn đại lý</option>{dealers.data?.items.map((row) => <option key={String(row.id)} value={String(row.id)}>{String(row.name)}</option>)}</select></label>}
        <small>Mật khẩu tối thiểu 12 ký tự. Gửi thông tin đăng nhập riêng cho người nhận.</small>
        <button className="primary" disabled={busy || (role === "dealer" && !dealers.data?.items.length)}>{busy ? "Đang lưu…" : "Tạo tài khoản"}</button>
      </fieldset></form>
  </dialog>;
}
