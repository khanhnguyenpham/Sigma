import { type Row } from "../../types/api";
import { fmt, text } from "../../utils/format";
import { Table } from "../ui/Table";
import { Card } from "../ui/Card";
import { DetailDrawer } from "../ui/DetailDrawer";
import { badge } from "../ui/Badge";
import type { PurchasingView } from "../../types/context";
import { Icon } from "../ui/Icon";
import { inventoryStatus } from "../../utils/supply";
import { warehouseName } from "../../utils/warehouse";
import { TradeRights, TradeQuantities } from "../products/TradePresentation";
import { isTradeRow, canRecommend } from "../../utils/trade";

export function InventoryDetails({
  focused,
  onClose,
  onItem,
}: {
  focused: Row;
  onClose: () => void;
  onItem?: (row: Row, page?: string, view?: PurchasingView) => void;
}) {
  return (
    <DetailDrawer title={text(focused.sku)} onClose={onClose}><InventoryInformation focused={focused} onItem={onItem} /></DetailDrawer>
  );
}

export function InventoryInformation({ focused, onItem }: { focused: Row; onItem?: (row: Row, page?: string, view?: PurchasingView) => void }) {
  return (
    <>
      <dl className="drawer-fields">
        <div>
          <dt>Kho</dt><dd>{warehouseName(focused)}</dd>
          {focused.receiving_warehouse_id != null && <><dt>Kho / tuyến nguồn</dt><dd>{String(focused.source_city ?? "—")}</dd></>}
        </div>
        <div><dt>Quốc gia</dt><dd>{text(focused.destination_country)}</dd></div>
        <div><dt>Nhà mạng</dt><dd>{text(focused.carrier)}</dd></div>
        <div>
          <dt>Loại sản phẩm</dt>
          <dd>{text(focused.product_type)}</dd>
        </div>
        <div>
          <dt>Ngày sổ tồn</dt>
          <dd>{text(focused.date)}</dd>
        </div>
        <div>
          <dt>Trạng thái</dt>
          <dd>
            {badge(inventoryStatus(focused))}
          </dd>
        </div>
      </dl>
      {isTradeRow(focused)?<><TradeRights row={focused} /><TradeQuantities row={focused} /></>:<>{focused.supply_status != null && <p>{badge(focused.supply_status)}</p>}{focused.replenishment_allowed === false && <p className="notice">Sản phẩm đã ngừng nhập trong kế hoạch này. Tiếp tục bán tồn và nhận lô đã đặt; không đặt thêm.</p>}</>}
      <div className="stats">
        <Card label="Tồn hiện có" value={fmt(focused.closing_qty)} />
        <Card label="Hàng đang về" value={fmt(focused.pending_qty)} />
        <Card label="Ngưỡng nhập" value={fmt(focused.rop)} />
        <Card
          label="Lượng cần đặt"
          value={fmt(focused.recommended_qty)}
          tone="orange"
        />
      </div>
      <h2>Chính sách nhập hàng</h2>
      <dl className="drawer-fields">
        <div>
          <dt>Tồn an toàn</dt>
          <dd>{fmt(focused.ss)}</dd>
        </div>
        <div><dt>Cách tính SS</dt><dd>{focused.safety_mode === "volatility" ? `Biến động ${fmt(focused.safety_lookback_days)} ngày · hệ số ${fmt(focused.safety_factor)}` : `Số ngày bán · ${fmt(focused.safety_days)} ngày`}</dd></div>
        <div><dt>Cách tính ROP</dt><dd>{focused.rop_mode === "fixed" ? "Cố định" : "Max(nhu cầu dự báo 7 ngày + SS, ngưỡng tối thiểu)"}</dd></div>
        <div><dt>N ngày cảnh báo xuống ROP</dt><dd>{fmt(focused.warning_horizon_days)}</dd></div>
        <div>
          <dt>Lượng nhập mỗi lần</dt>
          <dd>{focused.fixed_order_qty == null ? "Chưa cấu hình" : fmt(focused.fixed_order_qty)}</dd>
        </div>
        <div>
          <dt>{focused.rop_mode === "fixed" ? "ROP cấu hình đã chốt" : "Ngưỡng nhập tối thiểu"}</dt>
          <dd>{fmt(focused.configured_rop_floor)}</dd>
        </div>
        <div>
          <dt>Vị thế tồn IP</dt>
          <dd>{fmt(focused.inventory_position)}</dd>
        </div>
        <div>
          <dt>Mức tồn mục tiêu S</dt>
          <dd>{fmt(focused.target_stock)}</dd>
        </div>
        <div>
          <dt>ETA nếu đặt</dt>
          <dd>{text(focused.eta_if_ordered)}</dd>
        </div>
      </dl>
      <details className="advanced-section">
        <summary>Chi tiết sổ tồn & cách tính</summary>
        <div className="drawer-body">
          <Table
            rows={[focused]}
            columns={[
              { key: "opening_qty", label: "Đầu ngày" },
              { key: "receipts_qty", label: "Nhận" },
              { key: "sales_qty", label: "Bán" },
              { key: "fulfilled_qty", label: "Đáp ứng" },
              { key: "shortage_qty", label: "Thiếu" },
              { key: "closing_qty", label: "Cuối ngày" },
            ]}
          />
          <div className="formula">
            <span>
              {focused.rop_mode === "fixed"
                ? `ROP cố định = ${fmt(focused.configured_rop_floor)}; không cộng SS lần nữa`
                : `ROP = max(nhu cầu dự báo 7 ngày + SS, ngưỡng tối thiểu) = max(${fmt(focused.rop_forecast)}, ${fmt(focused.configured_rop_floor)}) = ${fmt(focused.rop)}`}
            </span>
            <span>
              IP = tồn cuối + đang về = {fmt(focused.inventory_position)}
            </span>
            <span>{focused.fixed_order_qty != null
              ? `Khi cần bổ sung: Q = ${fmt(focused.fixed_order_qty)} đơn vị mỗi lần, không tự tăng để bù đủ S.`
              : "Thiết lập lượng nhập mỗi lần trong cấu hình sản phẩm."}</span>
          </div>
          <p className="caption">
            Chỉ đề xuất khi tồn cuối &lt; ROP. Có thể Q=0 khi hàng đang về đủ
            mức mục tiêu. Policy v{text(focused.policy_version)} · L7/R1/H14.
          </p>
        </div>
      </details>
      {onItem && (
        <div className="drawer-actions">
          <button
            className="primary"
            onClick={() =>
              onItem(
                focused,
                "replenishment",
                canRecommend(focused)
                  ? "recommendations"
                  : "incoming",
              )
            }
          >
            {canRecommend(focused)
              ? "Xem đề xuất nhập"
              : "Xem hàng đang về"}
            <Icon name="arrow" size={16} />
          </button>
          <button
            className="secondary"
            onClick={() => onItem(focused, "alerts")}
          >
            Xem cảnh báo
          </button>
        </div>
      )}
    </>
  );
}
