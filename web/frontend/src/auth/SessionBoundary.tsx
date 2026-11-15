import { createContext, useContext, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { api, ApiError, setCsrfToken } from "../services/http";
import { State } from "../components/ui/State";
import { SupplierPortal } from "./SupplierPortal";
import { UserManagement } from "./UserManagement";
import { Icon } from "../components/ui/Icon";
import { ChangePassword } from "./ChangePassword";

export interface User { id: number; username: string; display_name: string; role: "admin" | "supplier"; supplier_id: number | null; active: boolean }
interface Session { required: boolean; user: User | null; csrf_token?: string }
const SessionContext = createContext<{ user: User; logout: () => Promise<void>; accounts: () => void; password: () => void } | null>(null);

export function AccountMenu() {
  const session = useContext(SessionContext);
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const outside = (event: PointerEvent) => { if (ref.current && !ref.current.contains(event.target as Node)) ref.current.open = false; };
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && ref.current?.open) {
        event.preventDefault(); ref.current.open = false; ref.current.querySelector("summary")?.focus();
      }
    };
    document.addEventListener("pointerdown", outside); document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("pointerdown", outside); document.removeEventListener("keydown", escape); };
  }, []);
  if (!session) return null;
  function close() { if (ref.current) ref.current.open = false; }
  const initials = session.user.display_name.split(/\s+/).filter(Boolean).slice(0, 2).map((word) => word[0]).join("");
  return <details className="account-menu" ref={ref} onBlur={(event) => {
    if (!event.currentTarget.contains(event.relatedTarget as Node | null)) close();
  }}><summary aria-label="Mở tài khoản"><span className="account-avatar" aria-hidden="true">{initials}</span>
      <span className="account-name">{session.user.display_name}</span><Icon name="chevron" size={13} /></summary>
    <div className="account-popover"><strong>{session.user.display_name}</strong><small>{session.user.role === "admin" ? "Quản trị viên" : "Nhà cung cấp"}</small>
      {session.user.role === "admin" && <button onClick={() => { close(); session.accounts(); }}>Tài khoản</button>}
      <button onClick={() => { close(); session.password(); }}>Đổi mật khẩu</button>
      <button onClick={() => { close(); void session.logout(); }}>Đăng xuất</button>
    </div></details>;
}

export function SessionBoundary({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error>();
  const [showAccounts, setShowAccounts] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  function accept(value: Session) {
    if (value.required && value.user?.role === "admin" && !location.hash && !new URLSearchParams(location.search).has("run_id"))
      history.replaceState(history.state, "", "?ops_tab=stock#operations");
    setCsrfToken(value.csrf_token ?? ""); setSession(value); setError(undefined);
  }
  useEffect(() => {
    let active = true;
    api<Session>("/auth/session").then((value) => { if (active) accept(value); }).catch((err: Error) => {
      if (!active) return;
      if (err instanceof ApiError && err.status === 401) accept({ required: true, user: null });
      else setError(err);
    }).finally(() => { if (active) setLoading(false); });
    const expired = () => { accept({ required: true, user: null }); setShowAccounts(false); setShowPassword(false); };
    window.addEventListener("sigma:unauthorized", expired);
    return () => { active = false; window.removeEventListener("sigma:unauthorized", expired); };
  }, []);
  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const fields = new FormData(form);
    setSubmitting(true); setError(undefined);
    try {
      accept(await api<Session>("/auth/login", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: String(fields.get("username")).trim().toLowerCase(), password: fields.get("password") }) }));
      form.reset();
    } catch (err) { setError(err as Error); }
    finally { setSubmitting(false); }
  }
  async function logout() {
    setSubmitting(true); setError(undefined);
    try { await api("/auth/logout", { method: "POST" }); accept({ required: true, user: null }); setShowAccounts(false); }
    catch (err) {
      if (err instanceof ApiError && err.status === 401) accept({ required: true, user: null });
      else setError(err as Error);
    } finally { setSubmitting(false); }
  }
  if (loading) return <div className="auth-page"><State loading /></div>;
  if (!session) return <div className="auth-page"><section className="auth-card"><h1>Không kết nối được hệ thống</h1><p role="alert">{error?.message}</p>
    <button onClick={() => window.location.reload()}>Thử lại</button></section></div>;
  if (!session.required) return <>{children}</>;
  if (!session.user) return <main className="auth-page"><section className="auth-brand"><span className="brand-mark">S</span>
    <p>SIGMA WORKSPACE</p><h1>Quản lý nhu cầu.<br />Chủ động tồn kho.</h1><p>Lập kế hoạch nhập SIM và gói data trên cùng một hệ thống.</p></section>
    <form className="auth-card" onSubmit={(event) => void login(event)} aria-busy={submitting}>
      <p className="eyebrow">CHÀO MỪNG TRỞ LẠI</p><h2>Đăng nhập SIGMA</h2><p>Sử dụng tài khoản được quản trị viên cấp.</p>
      <label>Tên đăng nhập<input name="username" autoComplete="username" required minLength={3} maxLength={64} disabled={submitting} /></label>
      <label>Mật khẩu<input name="password" type="password" autoComplete="current-password" required maxLength={128} disabled={submitting} /></label>
      {error && <p className="notice error" role="alert">{error.message}</p>}
      <button className="primary" disabled={submitting}>{submitting ? "Đang đăng nhập…" : "Đăng nhập"}</button>
      <small>Quên mật khẩu? Liên hệ quản trị viên để được hỗ trợ.</small>
    </form></main>;
  return <SessionContext.Provider value={{ user: session.user, logout, accounts: () => setShowAccounts(true), password: () => setShowPassword(true) }}>
    <div key={session.user.id} aria-busy={submitting}>
      {error && <div className="notice error" role="alert">{error.message}</div>}
      {session.user.role === "supplier" ? <SupplierPortal /> : children}
      {showAccounts && session.user.role === "admin" && <UserManagement currentId={session.user.id} onClose={() => setShowAccounts(false)} />}
      {showPassword && <ChangePassword onClose={() => setShowPassword(false)} />}
    </div>
  </SessionContext.Provider>;
}
