import { AlertDetails } from "../components/alerts/AlertDetails";
import { useEffect, useState } from "react";

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

import { PlanRequired } from "../components/ui/PlanRequired";
import type { PurchasingView } from "../types/context";
import { Icon } from "../components/ui/Icon";
import type { WorkspaceData } from "../types/api";
import { alertTypeLabel } from "../utils/labels";
import { warehouseName } from "../utils/warehouse";
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
    [alertType, setAlertType] = useState(""),
    [page, setPage] = useState(1),
    [selection, setSelection] = useState<{ key: string; row: Row }>();
  const key = JSON.stringify([ctx, state, alertType]);
  const focused = selection?.key === key ? selection.row : undefined;
  useEffect(() => setPage(1), [key]);
  const ready =
    run?.status === "complete" &&
    ["policy_replay", "alert_replay", "stock_projection"].includes(run.kind);
  const q = resultQuery(ctx, {
    as_of_date: ctx.origin,
    state,
    alert_type: alertType,
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
  const thresholdMetric = run?.status === "complete"
    ? run.result_summary.threshold_metrics as Row | undefined : undefined;

  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Cảnh báo tồn kho</h1>
          <p>Phân biệt dự kiến xuống ngưỡng nhập với ngày cạn dự kiến.</p>
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
              label="Dự kiến xuống ROP"
              value={fmt(summary.data?.summary.projected_below_rop_items)}
              note="Số mặt hàng duy nhất trong N ngày của policy"
              icon="clock"
            />
            <Card
              label="Mặt hàng có cảnh báo"
              value={fmt(summary.data?.summary.warning_items)}
              note="Một mặt hàng có nhiều tín hiệu vẫn chỉ tính một lần"
              tone="teal"
              icon="clock"
            />
          </div>
          <State error={summary.error} loading={summary.loading} />
          <Panel
            title="Danh sách cảnh báo"
            note={`Ngày ${ctx.origin} · Nhấn một dòng để xem diễn biến tồn dự kiến.`}
            action={
              <div className="segments">
              <select aria-label="Loại tín hiệu cảnh báo" value={alertType} onChange={(e) => setAlertType(e.target.value)}>
                <option value="">Tất cả tín hiệu</option>
                <option value="below_rop">Dưới ngưỡng nhập</option>
                <option value="projected_below_rop">Dự kiến xuống ROP</option>
                <option value="depletion">Nguy cơ cạn</option>
              </select>
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
                <option value="threshold_warning">Dự kiến xuống ROP</option>
                <option value="not_within_horizon">
                  Chưa cạn trong 14 ngày
                </option>
              </select>
              </div>
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
                    key: "city",
                    label: "Kho",
                    render: (_v, r) => (
                      <div className="cell-product">
                        <strong>{warehouseName(r)}</strong>
                        <small>{String(r.destination_country)}</small>
                      </div>
                    ),
                  },
                  { key: "carrier", label: "Nhà mạng" },
                  {
                    key: "alert_type",
                    label: "Tín hiệu",
                    render: alertTypeLabel,
                  },
                  { key: "state", label: "Trạng thái", render: badge },
                  { key: "rop", label: "ROP tại quyết định", render: (_, row) => fmt((((row.explanation as Row)?.thresholds) as Row)?.rop) },
                  { key: "warning_horizon_days", label: "N ngày", render: (_, row) => fmt((((row.explanation as Row)?.policy) as Row)?.warning_horizon_days ?? 7) },
                  { key: "predicted_threshold_date", label: "Xuống ROP dự kiến" },
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
            <p className="caption">{fmt(data.data?.total)} dòng tín hiệu trong bộ lọc; tổng mặt hàng trên thẻ được tính duy nhất theo kho, mặt hàng và ngày đang xem.</p>
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
                Metric depletion toàn lượt replay; không áp dụng bộ lọc bảng. Mục tiêu làm việc ≥45% với báo trước ≥7 ngày theo lời mentor được thuật lại; tính bắt buộc/phạm vi nghiệm thu còn cần làm rõ.
              </p>
              <AlertOpportunity run={run} />
            </details>
          )}
          {thresholdMetric && <details className="advanced-section">
            <summary>Đánh giá xuống ROP · riêng ngày cạn</summary>
            <div className="stats">
              <Card label="Sự kiện xuống ROP" value={fmt(thresholdMetric.event_denominator)} note={`${fmt(thresholdMetric.signal_count)} tín hiệu · ${fmt(thresholdMetric.evaluated_count)} ca hợp lệ`} />
              <Card label="Precision xuống ROP" value={pct(thresholdMetric.precision)} />
              <Card label="Recall xuống ROP" value={pct(thresholdMetric.recall)} />
              <Card label="Ca đã dưới ROP tại origin" value={fmt(thresholdMetric.excluded_count)} />
            </div>
            <p className="caption">Metric toàn alert replay, dùng ROP tại origin và N của từng policy; không áp dụng bộ lọc bảng, không cộng vào tỷ lệ báo trước ngày cạn ≥7 ngày. Sai số ngày xuống ROP: {fmt(thresholdMetric.date_mae, 2)} ngày.</p>
            <p className="caption">TP {fmt(thresholdMetric.TP)} · FP {fmt(thresholdMetric.FP)} · FN {fmt(thresholdMetric.FN)} · TN {fmt(thresholdMetric.TN)}</p>
          </details>}
        </>
      )}
      {focused && (
        <AlertDetails
          focused={focused}
          onClose={() => setSelection(undefined)}
          onItem={onItem}
        />
      )}
    </>
  );
}
