import { type PurchasingView } from "../../types/context";
import { type Page, type Row } from "../../types/api";
import { fmt, text } from "../../utils/format";
import { badge } from "../ui/Badge";
import { DetailDrawer } from "../ui/DetailDrawer";
import { Icon } from "../ui/Icon";

export function PurchasingDetails({
  focused,
  onClose,
  onItem,
  view,
  data,
  selectView,
}: {
  focused: Row;
  onClose: () => void;
  onItem?: (row: Row, page?: string, view?: PurchasingView) => void;
  view: PurchasingView;
  data?: Page;
  selectView: (view: PurchasingView) => void;
}) {
  return (
    <DetailDrawer
      eyebrow={
        view === "recommendations" ? "Đề xuất nhập hàng" : "Chi tiết lô nhập"
      }
      title={
        view === "recommendations" ? String(focused.sku) : `Lô #${focused.id}`
      }
      onClose={onClose}
    >
      <div className="detail-product">
        <span className="detail-product-icon">
          <Icon name={view === "recommendations" ? "box" : "truck"} />
        </span>
        <div>
          <strong>{text(focused.sku)}</strong>
          <p>
            {text(focused.carrier)} · {text(focused.destination_country)} ·{" "}
            {text(focused.product_type)}
          </p>
        </div>
      </div>
      {view === "recommendations" ? (
        <>
          <div className="decision-callout">
            <span>Đề xuất bổ sung</span>
            <strong>
              {fmt(focused.recommended_qty)} <small>đơn vị</small>
            </strong>
            <p>
              Tồn {fmt(focused.closing_qty)} thấp hơn ngưỡng {fmt(focused.rop)}.
              {focused.fixed_order_qty != null
                ? " Mỗi lần dùng đúng lượng đã cấu hình; mức tồn mục tiêu chỉ để tham chiếu."
                : " Phương án cũ tính lượng theo nhu cầu và MOQ."}
            </p>
          </div>
          <dl className="drawer-fields">
            <div>
              <dt>Tồn hiện có</dt>
              <dd>{fmt(focused.closing_qty)}</dd>
            </div>
            <div>
              <dt>Hàng đang về</dt>
              <dd>{fmt(focused.pending_qty)}</dd>
            </div>
            <div>
              <dt>Vị thế tồn (IP)</dt>
              <dd>{fmt(focused.inventory_position)}</dd>
            </div>
            <div>
              <dt>Mức tồn mục tiêu</dt>
              <dd>{fmt(focused.target_stock)}</dd>
            </div>
            <div>
              <dt>{focused.fixed_order_qty != null ? "Lượng nhập mỗi lần" : "MOQ của phương án cũ"}</dt>
              <dd>{fmt(focused.fixed_order_qty ?? focused.moq)}</dd>
            </div>
            <div>
              <dt>Nhận nếu đặt tại mốc</dt>
              <dd>{text(focused.eta_if_ordered)}</dd>
            </div>
          </dl>
          <p className="caption">
            Đây là khuyến nghị trong kế hoạch mô phỏng, chưa phát sinh lô nhập
            hoặc gửi đơn cho nhà cung cấp.
          </p>
        </>
      ) : (
        <>
          <div className="lot-summary">
            {badge(focused.status)}
            <strong>
              {fmt(focused.ordered_qty)} <small>đơn vị</small>
            </strong>
          </div>
          <div className="delivery-timeline">
            <div>
              <i />
              <span>Ngày đặt</span>
              <strong>{text(focused.ordered_on)}</strong>
            </div>
            <div>
              <i />
              <span>Dự kiến nhận · sau 7 ngày</span>
              <strong>{text(focused.eta)}</strong>
            </div>
          </div>
          <dl className="drawer-fields">
            <div>
              <dt>Đã nhận tại mốc dữ liệu</dt>
              <dd>{fmt(focused.received_qty)}</dd>
            </div>
            <div>
              <dt>Nhà cung cấp</dt>
              <dd>
                {focused.supplier_id ? `NCC #${focused.supplier_id}` : "—"}
              </dd>
            </div>
            <div>
              <dt>Phiên bản chính sách</dt>
              <dd>{text(focused.policy_version)}</dd>
            </div>
            <div>
              <dt>Mốc dữ liệu</dt>
              <dd>{text(data?.context?.known_orders_through)}</dd>
            </div>
          </dl>
        </>
      )}
      {onItem && (
        <div className="drawer-actions">
          <button
            className="primary"
            onClick={() => onItem(focused, "inventory")}
          >
            Mở hồ sơ tồn kho <Icon name="arrow" size={16} />
          </button>
          {view === "recommendations" && (
            <button
              className="secondary"
              onClick={() => {
                onClose();
                selectView("incoming");
              }}
            >
              Xem hàng đang về
            </button>
          )}
        </div>
      )}
    </DetailDrawer>
  );
}
