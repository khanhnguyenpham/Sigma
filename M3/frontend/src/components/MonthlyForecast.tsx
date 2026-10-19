import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { useEffect, useState } from "react";
import {
  useResource,
  Card,
  Panel,
  State,
  Table,
  Pager,
  ExportButton,
} from "./common";
import {
  type Run,
  type Context,
  type Page,
  type Row,
  query,
  fmt,
  pct,
} from "../api/client";

interface Benchmark {
  context: Row;
  summary: Row & { baselines: Row[] };
}

export function MonthlyForecast({ run, ctx }: { run?: Run; ctx: Context }) {
  const [page, setPage] = useState(1);
  const [cadence, setCadence] = useState("daily_origins");
  const [topOnly, setTopOnly] = useState(true);
  const ready = run?.status === "complete";
  const base = ready ? `/runs/${run.id}` : null;
  const scope = query({
    warehouse_id: ctx.warehouseId,
    top10_only: String(topOnly),
  });
  const q = `${scope}&${query({ as_of_date: ctx.origin, page, page_size: 50 })}`;
  const summary = useResource<Benchmark>(
    base ? `${base}/monthly-summary` : null,
  );
  const forecasts = useResource<Page>(
    base ? `${base}/monthly-forecasts?${q}` : null,
  );
  const metrics = useResource<Page>(
    base
      ? `${base}/monthly-metrics?${scope}&split=test&cadence=${cadence}&page_size=100`
      : null,
  );
  useEffect(
    () => setPage(1),
    [ctx.runId, ctx.warehouseId, ctx.origin, topOnly],
  );
  const s = summary.data?.summary;
  const rows = forecasts.data?.items ?? [];
  const benchmark = summary.data?.context;
  return (
    <>
      {!ready && (
        <div className="notice">
          Chọn một lượt đã hoàn tất để đối chiếu benchmark cùng nguồn dữ liệu.
        </div>
      )}
      <State loading={summary.loading} error={summary.error} />
      {s && (
        <>
          <div className="stats">
            <Card
              label="R05 · Tổng 30 ngày"
              value={`${fmt(s.routes_below_20_pct)}/${fmt(s.expected_top_routes)}`}
              note={
                s.meets_r05
                  ? "Từng tuyến top 10 đạt MAPE ≤20%"
                  : "Chưa đủ 10 tuyến đạt ngưỡng"
              }
              tone={s.meets_r05 ? "teal" : ""}
            />
            <Card
              label="MAPE trung bình top 10"
              value={`${fmt(s.mean_mape_positive_pct, 2)}%`}
              note="Test · origin hằng ngày · actual dương"
            />
            <Card
              label="Độ phủ tối thiểu"
              value={pct(s.minimum_coverage)}
              note={`${fmt(s.pairs_per_route)} cửa sổ đầy đủ / tuyến`}
            />
            <Card
              label="Cửa sổ dự báo"
              value="30 ngày"
              note="D+1…D+30 · lượng bán theo UTC"
            />
          </div>
          <div className="notice subtle">
            <strong>Tiêu chí mentor · M05.</strong> Chấm tổng lượng bán
            D+1…D+30, không phải tháng dương lịch. Bảng tổng kết gồm toàn bộ top
            10 theo train và không đổi theo bộ lọc. Đây là kết quả hồi cứu:
            hướng tinh chỉnh từng được chọn sau khi xem test; không phải holdout
            độc lập.
          </div>
        </>
      )}
      <Panel
        title="Dự báo tổng 30 ngày"
        note={`Origin ${ctx.origin || "tất cả"} · mỗi cửa sổ có đúng 30 ngày UTC`}
        action={
          <label>
            <input
              type="checkbox"
              checked={topOnly}
              onChange={(e) => setTopOnly(e.target.checked)}
            />{" "}
            Chỉ top 10 train
          </label>
        }
      >
        <State
          loading={forecasts.loading}
          error={forecasts.error}
          empty={!forecasts.loading && !forecasts.error && !rows.length}
        />
        {(ctx.itemId || ctx.productType || ctx.supplierId) && (
          <p className="caption">
            Tổng 30 chấm theo tuyến; bộ lọc SKU, loại sản phẩm và đối tác chỉ
            dùng ở các màn hình vận hành.
          </p>
        )}
        {rows.length > 0 && (
          <>
            <p className="caption">
              Biểu đồ tối đa 10 dòng đầu trang. Actual của cửa sổ chưa quan sát
              đủ 30 ngày để trống; không thay bằng 0.
            </p>
            <div className="chart">
              <ResponsiveContainer width="100%" height={270}>
                <BarChart
                  data={rows
                    .slice(0, 10)
                    .map((r) => ({
                      ...r,
                      route_label: `${r.destination_country} / ${r.carrier}`,
                    }))}
                >
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="route_label" tick={{ fontSize: 10 }} />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar
                    dataKey="forecast_qty"
                    name="Dự báo tổng 30"
                    fill="#087e86"
                  />
                  <Bar
                    dataKey="actual_qty"
                    name="Actual tổng 30"
                    fill="#d39448"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <Table
              rows={rows}
              columns={[
                { key: "destination_country", label: "Điểm đến" },
                { key: "carrier", label: "Nhà mạng" },
                { key: "window_start", label: "Từ D+1" },
                { key: "target_date", label: "Đến D+30" },
                { key: "forecast_qty", label: "Dự báo" },
                { key: "actual_qty", label: "Actual" },
                { key: "model", label: "Mô hình" },
                {
                  key: "metric_eligible",
                  label: "Đủ cửa sổ chấm",
                  render: (v) => (v ? "Có" : "Không"),
                },
              ]}
            />
            <Pager
              page={page}
              total={forecasts.data?.total ?? 0}
              onChange={setPage}
            />
            {base && (
              <ExportButton url={`${base}/exports/monthly_forecasts?${q}`} />
            )}
          </>
        )}
      </Panel>
      <Panel
        title="Sai số tổng 30 · test lịch sử"
        note="Chỉ cửa sổ nằm trọn 01/10–31/12/2025. Metric toàn kỳ, không phụ thuộc origin đang vẽ."
        action={
          <select
            aria-label="Nhịp chấm tổng 30"
            value={cadence}
            onChange={(e) => setCadence(e.target.value)}
          >
            <option value="daily_origins">
              Origin hằng ngày · tiêu chí chính
            </option>
            <option value="nonoverlapping_30d">
              Cửa sổ không chồng · chẩn đoán
            </option>
          </select>
        }
      >
        <State loading={metrics.loading} error={metrics.error} />
        <Table
          rows={metrics.data?.items ?? []}
          columns={[
            { key: "destination_country", label: "Điểm đến" },
            { key: "carrier", label: "Nhà mạng" },
            { key: "mape_positive_pct", label: "MAPE (%)" },
            { key: "mae", label: "MAE" },
            { key: "wape_pct", label: "WAPE (%)" },
            { key: "bias", label: "Bias" },
            { key: "coverage", label: "Độ phủ", render: pct },
            { key: "n_scored_pairs", label: "Cặp chấm" },
            {
              key: "passes_20_pct",
              label: "≤20%",
              render: (v) => (v ? "Đạt" : "Chưa đạt"),
            },
          ]}
        />
        <p className="caption">
          Actual 0 vẫn được tính vào MAE, WAPE và bias. Origin hằng ngày tạo các
          cửa sổ chồng nhau; 63 cửa sổ không phải 63 mẫu độc lập.
        </p>
        {base && (
          <ExportButton
            url={`${base}/exports/monthly_metrics?${scope}&split=test&cadence=${cadence}`}
          />
        )}
      </Panel>
      {s && (
        <Panel
          title="So sánh cùng tập cửa sổ · toàn bộ top 10"
          note="Naive và MA chỉ dùng dữ liệu đến origin; cùng 63 cửa sổ / tuyến, không đổi tập chấm."
        >
          <Table
            rows={s.baselines}
            columns={[
              { key: "model", label: "Phương pháp" },
              { key: "mean_mape_positive_pct", label: "MAPE trung bình (%)" },
              { key: "routes_below_20_pct", label: "Số tuyến ≤20% / 10" },
            ]}
          />
        </Panel>
      )}
      {benchmark && (
        <div className="notice subtle">
          <strong>Nguồn kết quả:</strong> {String(benchmark.benchmark_run_id)} ·
          xác minh {String(benchmark.verified_at_utc)}.<br />
          Gói {String(benchmark.benchmark_package_id).slice(0, 12)} ·{" "}
          {String(benchmark.acceptance_version)}. Benchmark 30 ngày dùng cùng
          source/target với lượt đang chọn; tồn và cảnh báo vẫn sử dụng forecast
          H14 riêng.
        </div>
      )}
    </>
  );
}
