import { fmt } from "../../utils/format";

export function Pager({
  page,
  total,
  onChange,
  pageSize = 50,
  loading = false,
}: {
  page: number;
  total: number;
  onChange: (page: number) => void;
  pageSize?: number;
  /** While a page loads, keep the last total and block another page change. */
  loading?: boolean;
}) {
  return (
    <div className="pager" aria-busy={loading}>
      <span>{fmt(total)} bản ghi</span>
      <button disabled={loading || page <= 1} onClick={() => onChange(page - 1)}>
        ← Trước
      </button>
      <span>Trang {page}</span>
      <button disabled={loading || page * pageSize >= total} onClick={() => onChange(page + 1)}>
        Sau →
      </button>
    </div>
  );
}
