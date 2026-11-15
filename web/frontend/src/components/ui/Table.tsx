import { fmt, text } from "../../utils/format";
import { type Row } from "../../types/api";

export type Column = {
  key: string;
  label: string;
  render?: (value: unknown, row: Row) => React.ReactNode;
};

export function Table({
  rows,
  columns,
  onRow,
  loading = false,
  stickyFirstColumn = false,
  emptyMessage = "Không có dữ liệu",
  label = "Bảng dữ liệu, có thể cuộn ngang",
}: {
  rows: Row[];
  columns: Column[];
  onRow?: (row: Row) => void;
  loading?: boolean;
  stickyFirstColumn?: boolean;
  emptyMessage?: string;
  label?: string;
}) {
  return (
    <div className={`table-scroll${stickyFirstColumn ? " sticky-first-column" : ""}`} role="region" aria-label={label} aria-busy={loading} tabIndex={0}>
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading ? Array.from({ length: 5 }, (_, row) => (
            <tr key={`loading-${row}`} aria-hidden="true">
              {columns.map((column) => <td key={column.key}><span className="skeleton-block" /></td>)}
            </tr>
          )) : rows.length === 0 ? (
            <tr><td colSpan={Math.max(1, columns.length)} className="table-empty">{emptyMessage}</td></tr>
          ) : rows.map((r, index) => (
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
                      ? Number.isFinite(r[c.key]) ? fmt(r[c.key], Number.isInteger(r[c.key]) ? 0 : 2) : "Không có"
                      : r[c.key] === null || r[c.key] === undefined || r[c.key] === "" ? "Không có" : text(r[c.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {loading && <span className="sr-only" role="status">Đang tải dữ liệu…</span>}
    </div>
  );
}
