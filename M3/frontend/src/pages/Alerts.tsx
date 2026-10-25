import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { AlertOpportunity } from "../components/alerts/AlertOpportunity";
import { type Run, type Page, type Row } from "../types/api";
import { type Context } from "../types/context";
import { resultQuery } from "../utils/url";
import { fmt, pct, text } from "../utils/format";
import { useResource } from "../hooks/useResource";
import { Panel } from "../components/ui/Panel";
import { State } from "../components/ui/State";
import { Table } from "../components/ui/Table";
import { Pager } from "../components/ui/Pager";
import { ExportButton } from "../components/ui/ExportButton";
import { badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";
import { DetailDrawer } from "../components/ui/DetailDrawer";
import { PlanRequired } from "../components/ui/PlanRequired";
import type { PurchasingView } from "../types/context";
import { Icon } from "../components/ui/Icon";
import type { WorkspaceData } from "../types/api";
export function Alerts({
  run,
  ctx,
  onChoose,
  onItem,
}: {
  run?: Run;
  ctx: Context;
  onChoose?: () => void;
  onItem?: (row: Row, page?: string, view?: PurchasingView) => void;
}) {
  const [state, setState] = useState(""),
    [page, setPage] = useState(1),
    [selection, setSelection] = useState<{ key: string; row: Row }>();
  const key = JSON.stringify([ctx, state]);
  const focused = selection?.key === key ? selection.row : undefined;
  useEffect(() => setPage(1), [key]);
  const ready =
    run?.status === "complete" &&
    ["policy_replay", "alert_replay", "stock_projection"].includes(run.kind);
  const q = resultQuery(ctx, {
    as_of_date: ctx.origin,
    state,
    page,
    page_size: 50,
  });
  const data = useResource<Page>(ready ? `/runs/${run.id}/alerts?${q}` : null);
  const summary = useResource<WorkspaceData>(
    ready && ctx.origin
      ? `/runs/${run.id}/workspace?${resultQuery(ctx, { as_of_date: ctx.origin })}`
      : null,
  );
  const rows = data.data?.items ?? [];
  const m =
    run?.status === "complete"
      ? (run.result_summary.alert_metrics as Row | undefined)
      : undefined;
  const explanation = focused?.explanation as Row | undefined;
  const projection = explanation?.projection as Row[] | undefined;
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Cảnh báo tồn kho</h1>
          <p>Ưu tiên các mặt hàng có nguy cơ cạn hoặc cần bổ sung.</p>
        </div>
        {ready && <ExportButton url={`/runs/${run.id}/exports/alerts?${q}`} />}
      </div>
      {!ready ? (
        <PlanRequired onChoose={onChoose} />
      ) : (
        <>
          <div className="stats">
            <Card
              label="Cần xử lý sớm"
              value={fmt(summary.data?.summary.urgent_items)}
              note="Nguy cơ cạn dưới 7 ngày hoặc đã hết"
              tone="red"
              icon="bell"
            />
            <Card
              label="Dưới ngưỡng nhập"
              value={fmt(summary.data?.summary.low_stock_items)}
              note="Theo số tồn của ngày đang chọn"
              tone="orange"
              icon="alert"
            />
            <Card
              label="Cần đặt thêm"
              value={fmt(summary.data?.summary.replenish_items)}
              note="Đã tính lượng hàng đang về"
              icon="truck"
            />
            <Card
              label="Hàng đang về"
              value={fmt(summary.data?.summary.pending_units)}
              note="Lượng đã đặt tại mốc đang xem"
              tone="teal"
              icon="clock"
            />
          </div>
          <State error={summary.error} loading={summary.loading} />
          <Panel
            title="Danh sách cảnh báo"
            note={`Ngày ${ctx.origin} · Nhấn một dòng để xem diễn biến tồn dự kiến.`}
            action={
              <select
                aria-label="Trạng thái cảnh báo"
                value={state}
                onChange={(e) => setState(e.target.value)}
              >
                <option value="">Tất cả trạng thái</option>
                <option value="urgent">Khẩn · dưới 7 ngày</option>
                <option value="early">Có thể cạn sau ít nhất 7 ngày</option>
                <option value="already_depleted">Đã hết tại mốc chốt</option>
                <option value="low_stock">Cần bổ sung</option>
                <option value="pending_covers">Đã đặt đủ hàng đang về</option>
                <option value="not_within_horizon">
                  Chưa cạn trong 14 ngày
                </option>
              </select>
            }
          >
            <State
              loading={data.loading}
              error={data.error}
              empty={!data.loading && !data.error && !rows.length}
            />
            {!data.loading && !data.error && rows.length > 0 && (
              <Table
                rows={rows}
                onRow={(row) => setSelection({ key, row })}
                columns={[
                  {
                    key: "sku",
                    label: "Mặt hàng",
                    render: (v, r) => (
                      <div className="cell-product">
                        <strong>{String(v)}</strong>
                        <small>{String(r.product_type)}</small>
                      </div>
                    ),
                  },
                  {
                    key: "carrier",
                    label: "Kho / tuyến",
                    render: (v, r) => (
                      <div className="cell-product">
                        <strong>{String(v)}</strong>
                        <small>{String(r.destination_country)}</small>
                      </div>
                    ),
                  },
                  {
                    key: "alert_type",
                    label: "Tín hiệu",
                    render: (v) =>
                      v === "depletion" ? "Nguy cơ cạn" : "Dưới ngưỡng nhập",
                  },
                  { key: "state", label: "Trạng thái", render: badge },
                  { key: "predicted_depletion_date", label: "Cạn dự kiến" },
                  { key: "lead_days", label: "Số ngày còn lại" },
                  {
                    key: "item_id",
                    label: "",
                    render: () => <Icon name="chevron" size={15} />,
                  },
                ]}
              />
            )}
            <Pager
              page={page}
              total={data.data?.total ?? 0}
              onChange={setPage}
            />
          </Panel>
          {m && (
            <details className="advanced-section">
              <summary>Đánh giá lịch sử & độ tin cậy cảnh báo</summary>
              <div className="stats">
                <Card
                  label="Báo sớm ≥7 ngày"
                  value={pct(m.early_rate)}
                  note={`${fmt(m.early_numerator)}/${fmt(m.event_denominator)} sự kiện`}
                />
                <Card label="Precision" value={pct(m.precision)} />
                <Card label="Recall" value={pct(m.recall)} />
                <Card label="Ca không chấm" value={fmt(m.excluded_count)} />
              </div>
              <p className="caption">
                Metric toàn lượt replay; không áp dụng bộ lọc bảng. Chưa có
                ngưỡng tỷ lệ tổng được mentor chốt.
              </p>
              <AlertOpportunity run={run} />
            </details>
          )}
        </>
      )}
      {focused && (
        <DetailDrawer
          title={text(focused.sku)}
          onClose={() => setSelection(undefined)}
        >
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
                Chỉ tính các lô đã biết và nhận đúng ETA đầu ngày. Chưa có
                actual tương lai; không đặt thêm lô trong dự phóng này.
              </p>
            </>
          ) : (
            <div className="notice">
              Tín hiệu dưới ngưỡng nhập. Mở Tồn kho để xem mức ROP, lượng đang
              về và đề xuất đặt thêm.
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
      )}
    </>
  );
}
