import { fmt } from "../../utils/format";

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
