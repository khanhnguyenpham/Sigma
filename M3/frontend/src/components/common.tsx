import { useEffect, useRef, useState } from "react";
import { api, fmt, text, errorLabel, type Row } from "../api/client";
export function useResource<T>(path: string | null, keepPrevious = false) {
  const [state, setState] = useState<{
    path: string | null;
    data?: T;
    loading: boolean;
    error?: Error;
  }>({ path, loading: !!path });
  useEffect(() => {
    const controller = new AbortController();
    if (!path) {
      setState({ path, loading: false });
      return () => controller.abort();
    }
    setState((previous) => ({
      path,
      data: keepPrevious ? previous.data : undefined,
      loading: true,
    }));
    api<T>(path, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setState({ path, data, loading: false });
      })
      .catch((error) => {
        if (!controller.signal.aborted) setState({ path, loading: false, error });
      });
    return () => controller.abort();
  }, [path]);
  return state.path === path || keepPrevious ? state : { loading: !!path, data: undefined, error: undefined };
}
export function useDialogFocus(open: boolean, onClose: () => void) {
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    const dialog = document.querySelector<HTMLElement>('[role="dialog"]');
    const targets = () =>
      Array.from(
        dialog?.querySelectorAll<HTMLElement>(
          'button:not(:disabled),input:not([type="hidden"]):not(:disabled),select:not(:disabled),textarea,a[href]',
        ) ?? [],
      ).filter((el) => el.getClientRects().length > 0);
    targets()[0]?.focus();
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        close.current();
      }
      if (event.key === "Tab") {
        const list = targets(),
          first = list[0],
          last = list.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      previous?.focus();
    };
  }, [open]);
}
export function State({
  loading,
  error,
  empty = false,
}: {
  loading?: boolean;
  error?: Error;
  empty?: boolean;
}) {
  if (loading)
    return (
      <div className="skeleton" role="status">
        Đang tải dữ liệu cùng lượt chạy…
      </div>
    );
  if (error)
    return (
      <div className="notice error" role="alert">
        {errorLabel(error)}
      </div>
    );
  if (empty)
    return (
      <div className="empty">
        Không có bản ghi phù hợp. Hãy đổi ngày hoặc xóa bộ lọc.
      </div>
    );
  return null;
}
export function Card({
  label,
  value,
  note,
  tone = "",
}: {
  label: string;
  value: string;
  note?: string;
  tone?: string;
}) {
  return (
    <article className={"stat " + tone}>
      <span>{label}</span>
      <strong>{value}</strong>
      {note && <small>{note}</small>}
    </article>
  );
}
export type Column = {
  key: string;
  label: string;
  render?: (value: unknown, row: Row) => React.ReactNode;
};
export function Table({
  rows,
  columns,
  onRow,
}: {
  rows: Row[];
  columns: Column[];
  onRow?: (row: Row) => void;
}) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, index) => (
            <tr
              key={String(r.id ?? r.item_id ?? index) + "_" + index}
              tabIndex={onRow ? 0 : undefined}
              onKeyDown={
                onRow
                  ? (e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onRow(r);
                      }
                    }
                  : undefined
              }
              onClick={() => onRow?.(r)}
              className={onRow ? "clickable" : ""}
            >
              {columns.map((c) => (
                <td key={c.key}>
                  {c.render
                    ? c.render(r[c.key], r)
                    : typeof r[c.key] === "number"
                      ? fmt(r[c.key], Number.isInteger(r[c.key]) ? 0 : 2)
                      : text(r[c.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function Pager({
  page,
  total,
  onChange,
}: {
  page: number;
  total: number;
  onChange: (page: number) => void;
}) {
  return (
    <div className="pager">
      <span>{fmt(total)} bản ghi</span>
      <button disabled={page <= 1} onClick={() => onChange(page - 1)}>
        ← Trước
      </button>
      <span>Trang {page}</span>
      <button disabled={page * 50 >= total} onClick={() => onChange(page + 1)}>
        Sau →
      </button>
    </div>
  );
}
export function Panel({
  title,
  note,
  children,
  action,
}: {
  title: string;
  note?: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-title">
        <div>
          <h2>{title}</h2>
          {note && <p>{note}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
export function ExportButton({ url }: { url: string }) {
  return (
    <a className="button secondary" href={"/api/v1" + url} download>
      ↓ Xuất CSV
    </a>
  );
}
export const badge = (value: unknown) => (
  <span className={"badge " + String(value)}>
    {(
      {
        early: "Sớm ≥7 ngày",
        urgent: "Khẩn · dưới 7 ngày",
        already_depleted: "Đã hết tại mốc chốt",
        not_within_horizon: "Chưa cạn trong 14 ngày",
        pending_covers: "Dưới ROP · đã đặt đủ",
        low_stock: "Cần bổ sung",
        complete: "Hoàn tất",
        running: "Đang chạy",
        queued: "Đang chờ",
        failed: "Lỗi",
        received: "Đã nhận",
        ordered: "Đang về",
      } as Record<string, string>
    )[String(value)] ?? text(value)}
  </span>
);
