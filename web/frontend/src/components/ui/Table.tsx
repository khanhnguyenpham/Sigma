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
