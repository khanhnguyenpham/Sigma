import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";
import { type Row } from "../../types/api";
import { fmt, text } from "../../utils/format";
import { badge } from "../ui/Badge";
import { DetailDrawer } from "../ui/DetailDrawer";
import type { PurchasingView } from "../../types/context";
import { Icon } from "../ui/Icon";
import { Table } from "../ui/Table";
import { alertTypeLabel } from "../../utils/labels";

export function AlertDetails({
  focused,
  onClose,
  onItem,
}: {
  focused: Row;
  onClose: () => void;
  onItem?: (row: Row, page?: string, view?: PurchasingView) => void;
}) {
  const explanation = focused?.explanation as Row | undefined;
  const projection = explanation?.projection as Row[] | undefined;
  const policy = explanation?.policy as Row | undefined;
  const thresholds = explanation?.thresholds as Row | undefined;
  const evaluation = explanation?.threshold_evaluation as Row | undefined;
  const projected = focused.alert_type === "projected_below_rop";
  return (
    <DetailDrawer title={text(focused.sku)} onClose={onClose}>
      <dl className="drawer-fields">
        <div>
          <dt>Kho / tuyến</dt>
          <dd>
            {text(focused.destination_country)} / {text(focused.carrier)}
          </dd>
        </div>
        <div>
          <dt>Loại tín hiệu</dt>
          <dd>
            {alertTypeLabel(focused.alert_type)}
          </dd>
        </div>
        <div>
          <dt>Trạng thái</dt>
          <dd>{badge(focused.state)}</dd>
        </div>
        <div>
          <dt>Ngày quyết định · UTC</dt><dd>{text(focused.as_of_date)}</dd>
        </div>
        <div><dt>Tồn tại quyết định</dt><dd>{fmt(explanation?.origin_on_hand)}</dd></div>
        <div><dt>ROP tại quyết định</dt><dd>{fmt(thresholds?.rop)}</dd></div>
        <div><dt>Cách tính ROP</dt><dd>{policy?.rop_mode === "fixed" ? "Cố định" : "Theo dự báo"}</dd></div>
        <div><dt>Tồn an toàn SS</dt><dd>{fmt(thresholds?.ss)}</dd></div>
        <div><dt>Cách tính SS</dt><dd>{policy?.safety_mode === "volatility" ? `Biến động · ${fmt(policy.safety_lookback_days)} ngày · hệ số ${fmt(policy.safety_factor)}` : `Số ngày bán · ${fmt(policy?.safety_days)} ngày`}</dd></div>
        <div><dt>N ngày nhìn trước ROP</dt><dd>{fmt(policy?.warning_horizon_days ?? 7)}</dd></div>
        <div><dt>Xuống ROP dự kiến</dt><dd>{text(focused.predicted_threshold_date)}</dd></div>
        <div>
          <dt>Cạn dự kiến</dt>
          <dd>{text(focused.predicted_depletion_date)}</dd>
        </div>
        <div><dt>Số ngày tới lúc cạn</dt><dd>{fmt(focused.lead_days)}</dd></div>
      </dl>
      <p className="notice subtle">
        {projected
          ? `Tồn tại quyết định chưa dưới ROP. Lần đầu tồn cuối ngày dự kiến < ROP là ${text(focused.predicted_threshold_date)} trong N ngày. Ngày cạn được đọc từ tín hiệu Nguy cơ cạn riêng của mặt hàng.`
          : focused.alert_type === "below_rop"
            ? focused.state === "pending_covers"
              ? "Tồn cuối ngày dưới ROP, nhưng lượng đang về đã đủ mức mục tiêu nên chưa đề xuất đặt thêm."
              : "Tồn cuối ngày dưới ROP; kiểm tra lượng đang về và đề xuất nhập."
            : "Ngày cạn là lần đầu tồn dự kiến chạm 0 trong H14; khác ngày tồn xuống dưới ROP. Báo sớm ≥7 ngày được đo riêng trong replay."}
      </p>
      {projection ? (
        <>
          <h2>Diễn biến tồn dự kiến</h2>
          <div className="chart">
            <ResponsiveContainer width="100%" height={245}>
              <LineChart data={projection}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke="#edf0f6"
                />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip formatter={(v) => fmt(v, 2)} />
                {thresholds?.rop != null && <ReferenceLine y={Number(thresholds.rop)} ifOverflow="extendDomain" stroke="#c99243" strokeDasharray="5 4" label="ROP tại quyết định" />}
                <Line
                  dataKey="closing_forecast"
                  name="Tồn dự kiến"
                  stroke="#5366df"
                  strokeWidth={2.5}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="caption">
            Chỉ tính các lô đã biết và nhận đúng ETA đầu ngày. Chưa có actual
            tương lai; không đặt thêm lô trong dự phóng này.
          </p>
          <details className="advanced-section">
            <summary>Bảng tồn dự kiến theo ngày UTC</summary>
            <Table rows={projection} columns={[
              { key: "date", label: "Ngày UTC" },
              { key: "receipts_qty", label: "Hàng đã biết về đầu ngày" },
              { key: "closing_forecast", label: "Tồn cuối ngày dự kiến" },
            ]} />
          </details>
        </>
      ) : (
        <div className="notice">
          Tín hiệu dưới ngưỡng nhập. Mở Tồn kho để xem mức ROP, lượng đang về và
          đề xuất đặt thêm.
        </div>
      )}
      <details className="advanced-section">
        <summary>Thông tin đánh giá lịch sử</summary>
        <div className="drawer-body">
          <dl className="drawer-fields">
            <div>
              <dt>{projected ? "Ngày xuống ROP trong replay" : "Ngày cạn trong replay"}</dt>
              <dd>{text(projected ? evaluation?.actual_threshold_date : focused.actual_depletion_date)}</dd>
            </div>
            <div>
              <dt>Đánh giá</dt>
              <dd>{text(focused.evaluation_class)}</dd>
            </div>
          </dl>
          {Boolean(focused.exclusion_reason) && (
            <p className="caption">
              Không chấm: {text(focused.exclusion_reason)}
            </p>
          )}
        </div>
      </details>
      {onItem && (
        <div className="drawer-actions">
          <button
            className="primary"
            onClick={() => onItem(focused, "inventory")}
          >
            Kiểm tra tồn kho <Icon name="arrow" size={16} />
          </button>
          <button
            className="secondary"
            onClick={() => onItem(focused, "replenishment")}
          >
            Xem kế hoạch nhập
          </button>
        </div>
      )}
    </DetailDrawer>
  );
}
