import { errorLabel } from "../../utils/labels";

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
        Không có bản ghi phù hợp. Hãy đổi ngày hoặc xóa bộ lọc.
      </div>
    );
  return null;
}
