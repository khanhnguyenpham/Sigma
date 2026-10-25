import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { type Row } from "../../types/api";
import { fmt, text } from "../../utils/format";
import { badge } from "../ui/Badge";
import { DetailDrawer } from "../ui/DetailDrawer";
import type { PurchasingView } from "../../types/context";
import { Icon } from "../ui/Icon";

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
            {focused.alert_type === "depletion"
              ? "Nguy cơ cạn"
              : "Dưới ngưỡng nhập"}
          </dd>
        </div>
        <div>
          <dt>Trạng thái</dt>
          <dd>{badge(focused.state)}</dd>
        </div>
        <div>
          <dt>Cạn dự kiến</dt>
          <dd>{text(focused.predicted_depletion_date)}</dd>
        </div>
      </dl>
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
              <dt>Ngày cạn trong replay</dt>
              <dd>{text(focused.actual_depletion_date)}</dd>
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
