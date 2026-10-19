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
import {
  type Run,
  type Context,
  type Page,
  type Row,
  resultQuery,
  fmt,
  pct,
  text,
} from "../api/client";
import {
  useResource,
  Panel,
  State,
  Table,
  Pager,
  ExportButton,
  badge,
  Card,
} from "../components/common";
export function Alerts({ run, ctx }: { run?: Run; ctx: Context }) {
  const [state, setState] = useState(""),
    [page, setPage] = useState(1),
    [focused, setFocused] = useState<Row>();
  useEffect(() => {
    setPage(1);
    setFocused(undefined);
  }, [
    ctx.runId,
    ctx.warehouseId,
    ctx.itemId,
    ctx.productType,
    ctx.supplierId,
    ctx.origin,
    state,
  ]);
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
  const rows = data.data?.items ?? [];
  const m = run?.result_summary.alert_metrics as Row | undefined;
  const explanation = focused?.explanation as Row | undefined;
  const projection = explanation?.projection as Row[] | undefined;
  return (
    <>
      <div className="page-intro">
        <span className="eyebrow">04 / RỦI RO CẠN</span>
        <h1>Phát hiện sớm, giải thích rõ.</h1>
        <p>
          Dưới ROP và ngày cạn là hai tín hiệu khác nhau. Cảnh báo không tự thêm
          lô nhập vào projection.
        </p>
      </div>
      {m && (
        <>
          <div className="stats">
            <Card
              label="Early rate toàn lượt replay"
              value={pct(m.early_rate)}
              note={`${fmt(m.early_numerator)}/${fmt(m.event_denominator)} sự kiện thực mô phỏng`}
              tone="teal"
            />
            <Card
              label="Precision"
              value={pct(m.precision)}
              note={`TP ${fmt(m.TP)} · FP ${fmt(m.FP)}`}
            />
            <Card
              label="Recall"
              value={pct(m.recall)}
              note={`FN ${fmt(m.FN)} · TN ${fmt(m.TN)}`}
            />
            <Card
              label="Đã cạn / bị loại"
              value={fmt(m.excluded_count)}
              note="Không đưa vào mẫu sự kiện tương lai"
              tone="orange"
            />
          </div>
          <p className="caption">
            Các tỷ lệ trên tổng hợp toàn lượt replay. Chưa có ngưỡng
            precision/recall được mentor chốt; không bảo đảm mọi ca báo
            trước7ngày.
          </p>
        </>
      )}
      {!ready ? (
        <div className="notice">
          Chọn một lượt tồn kho đã hoàn tất. Chỉ alert replay có confusion
          matrix.
        </div>
      ) : (
        <Panel
          title={`Tín hiệu tại ${ctx.origin}`}
          note="Nhấn một dòng để xem tồn đầu, receipts đã biết và đường tồn dự kiến."
          action={
            <select
              aria-label="Trạng thái cảnh báo"
              value={state}
              onChange={(e) => setState(e.target.value)}
            >
              <option value="">Tất cả trạng thái</option>
              <option value="urgent">Khẩn · dưới7ngày</option>
              <option value="early">Sớm · từ7ngày</option>
              <option value="already_depleted">Đã cạn tại origin</option>
              <option value="low_stock">Dưới ROP · cần nhập</option>
              <option value="pending_covers">Dưới ROP · pending đủ</option>
              <option value="not_within_horizon">Chưa cạn trongH14</option>
            </select>
          }
        >
          <State
            loading={data.loading}
            error={data.error}
            empty={!data.loading && !data.error && !rows.length}
          />
          <Table
            rows={rows}
            onRow={setFocused}
            columns={[
              { key: "carrier", label: "Nhà mạng" },
              { key: "sku", label: "SKU" },
              {
                key: "alert_type",
                label: "Tín hiệu",
                render: (v) => (v === "depletion" ? "Nguy cơ cạn" : "Dưới ROP"),
              },
              { key: "state", label: "Trạng thái", render: badge },
              { key: "predicted_depletion_date", label: "Cạn dự kiến" },
              { key: "lead_days", label: "Số ngày" },
              { key: "actual_depletion_date", label: "Cạn replay" },
              { key: "evaluation_class", label: "Đánh giá" },
            ]}
          />
          <Pager page={page} total={data.data?.total ?? 0} onChange={setPage} />
          <ExportButton url={`/runs/${run.id}/exports/alerts?${q}`} />
        </Panel>
      )}
      {focused && (
        <Panel
          title={`${text(focused.sku)} · ${focused.alert_type === "depletion" ? "Projection14 ngày" : "Policy đã áp dụng"}`}
          note="Receipts được cộng đúng ETA đầu ngày; không lấy actual tương lai để tạo cảnh báo."
        >
          {projection ? (
            <div className="chart">
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={projection}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                  <YAxis />
                  <Tooltip />
                  <Line
                    dataKey="closing_forecast"
                    name="Tồn dự kiến"
                    stroke="#087e86"
                    strokeWidth={2.5}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : null}
          <p className="caption">
            {focused.exclusion_reason
              ? `Không chấm: ${text(focused.exclusion_reason)}`
              : "Kết quả cảnh báo phải đọc cùng loại replay và mẫu số."}
          </p>
        </Panel>
      )}
    </>
  );
}
