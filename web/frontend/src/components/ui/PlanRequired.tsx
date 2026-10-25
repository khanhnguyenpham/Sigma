import { Icon } from "./Icon";

export function PlanRequired({ onChoose }: { onChoose?: () => void }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <Icon name="box" size={28} />
      </div>
      <h2>Chọn một kế hoạch tồn kho</h2>
      <p>
        Mở kế hoạch đã xử lý để xem tồn, hàng đang về và cảnh báo. Bạn cũng có
        thể tạo phương án mới.
      </p>
      {onChoose && (
        <button className="primary" onClick={onChoose}>
          Mở kế hoạch tồn kho <Icon name="arrow" size={16} />
        </button>
      )}
    </div>
  );
}
