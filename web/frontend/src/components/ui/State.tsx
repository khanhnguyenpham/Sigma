import { errorLabel } from "../../utils/labels";

export function State({
  loading,
  error,
  empty = false,
  emptyMessage = "Không có bản ghi phù hợp. Hãy đổi ngày hoặc xóa bộ lọc.",
}: {
  loading?: boolean;
  error?: Error;
  empty?: boolean;
  emptyMessage?: string;
}) {
  if (loading)
    return (
      <div className="skeleton" role="status" aria-busy="true" aria-live="polite">
        <span className="sr-only">Đang tải dữ liệu…</span>
        <span className="skeleton-block" aria-hidden="true" />
        <span className="skeleton-block" aria-hidden="true" />
        <span className="skeleton-block" aria-hidden="true" />
      </div>
    );
  if (error)
    return (
      <div className="notice error" role="alert">
        <span>{errorLabel(error)}</span>
        <button
          className="secondary"
          onClick={() => window.dispatchEvent(new Event("sigma:refresh"))}
        >
          Thử tải lại
        </button>
      </div>
    );
  if (empty)
    return (
      <div className="empty">
        {emptyMessage}
      </div>
    );
  return null;
}
