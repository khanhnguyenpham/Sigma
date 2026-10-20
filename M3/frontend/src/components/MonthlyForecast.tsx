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
import { Icon } from "./Icon";
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
  const [page, setPage] = useState(1),
    [cadence, setCadence] = useState("daily_origins"),
    [topOnly, setTopOnly] = useState(false);
  const ready = run?.status === "complete" && !!ctx.origin;
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
  const s = summary.data?.summary,
    rows = forecasts.data?.items ?? [],
    benchmark = summary.data?.context;
  const full = rows.length > 0 && rows.length === forecasts.data?.total;
  const total = full
    ? rows.reduce((sum, r) => sum + Number(r.forecast_qty), 0)
    : null;
  const actual =
    full && rows.every((r) => typeof r.actual_qty === "number")
      ? rows.reduce((sum, r) => sum + Number(r.actual_qty), 0)
      : null;
  return (
    <>
      {!ready && (
        <div className="notice">
          Chọn phương án đã hoàn tất và ngày làm việc để xem dự báo.
        </div>
      )}
      <div className="stats forecast-kpis">
        <Card
          label="Nhu cầu dự kiến"
          value={fmt(total, 1)}
          note="Tổng lượng bán trong 30 ngày tiếp theo"
          icon="chart"
        />
        <Card
          label="Tuyến đang xem"
          value={forecasts.data ? fmt(forecasts.data.total) : "—"}
          note={
            topOnly
              ? "Tuyến chủ lực theo dữ liệu train"
              : "Theo bộ lọc kho / tuyến"
          }
          icon="grid"
        />
        <Card
          label="Thực tế cùng kỳ"
          value={fmt(actual, 0)}
          note={
            actual === null
              ? "Chưa có đủ actual cho cửa sổ này"
              : "Lượng bán đã quan sát đủ 30 ngày"
          }
          icon="box"
        />
        <Card
          label="Kỳ kế hoạch"
          value="30 ngày"
          note="Từ D+1 đến D+30 theo UTC"
          tone="teal"
          icon="clock"
        />
      </div>
      <Panel
        title="Nhu cầu theo tuyến"
        note={`Ngày lập ${ctx.origin || "chưa chọn"} · Tổng lượng bán D+1…D+30.`}
        action={
          <div className="panel-actions">
            <label className="monthly-toggle">
              <input
                type="checkbox"
                checked={topOnly}
                onChange={(e) => setTopOnly(e.target.checked)}
              />
              Chỉ tuyến chủ lực
            </label>
            {base && (
              <ExportButton url={`${base}/exports/monthly_forecasts?${q}`} />
            )}
          </div>
        }
      >
        <State
          loading={forecasts.loading}
          error={forecasts.error}
          empty={!forecasts.loading && !forecasts.error && !rows.length}
        />
        {(ctx.itemId || ctx.productType || ctx.supplierId) && (
          <p className="caption">
            Dự báo tổng 30 theo toàn tuyến. Bộ lọc mặt hàng, loại và nhà cung
            cấp áp dụng cho tồn kho hoặc phân bổ ngày.
          </p>
        )}
        {rows.length > 0 && (
          <>
            <div className="chart">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart
                  data={rows
                    .slice(0, 12)
                    .map((r) => ({ ...r, route_label: r.carrier }))}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    vertical={false}
                    stroke="#edf0f6"
                  />
                  <XAxis
                    dataKey="route_label"
                    tick={{ fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    formatter={(v) => fmt(v, 2)}
                    labelFormatter={(_, payload) =>
                      payload[0]?.payload?.destination_country +
                      " / " +
                      payload[0]?.payload?.carrier
                    }
                  />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                  <Bar
                    dataKey="forecast_qty"
                    name="Dự kiến"
                    fill="#6171e5"
                    radius={[3, 3, 0, 0]}
                    maxBarSize={26}
                  />
                  <Bar
                    dataKey="actual_qty"
                    name="Thực tế"
                    fill="#bec8f0"
                    radius={[3, 3, 0, 0]}
                    maxBarSize={26}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="caption">
              Biểu đồ 12 tuyến đầu trang. Actual chưa đủ 30 ngày để trống.
            </p>
            <Table
              rows={rows}
              columns={[
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
                { key: "window_start", label: "Từ ngày" },
                { key: "target_date", label: "Đến ngày" },
                {
                  key: "forecast_qty",
                  label: "Lượng dự kiến",
                  render: (v) => (
                    <strong className="forecast-value">{fmt(v, 1)}</strong>
                  ),
                },
                { key: "actual_qty", label: "Thực tế" },
                {
                  key: "metric_eligible",
                  label: "Dữ liệu thực tế",
                  render: (_, r) => (
                    <span
                      className={
                        "badge " +
                        (r.actual_qty === null ? "queued" : "complete")
                      }
                    >
                      {r.actual_qty === null ? "Chưa đủ nhãn" : "Đã quan sát"}
                    </span>
                  ),
                },
              ]}
            />
            <Pager
              page={page}
              total={forecasts.data?.total ?? 0}
              onChange={setPage}
            />
          </>
        )}
      </Panel>
      <details className="advanced-section">
        <summary>
          <Icon name="info" size={16} />
          Chất lượng & nguồn dự báo
        </summary>
        <State loading={summary.loading} error={summary.error} />
        {s && (
          <>
            <div className="stats">
              <Card
                label="Tuyến chủ lực đạt MAPE ≤20%"
                value={`${fmt(s.routes_below_20_pct)}/${fmt(s.expected_top_routes)}`}
                note="Toàn bộ top 10 theo train"
              />
              <Card
                label="MAPE trung bình top 10"
                value={fmt(s.mean_mape_positive_pct, 2) + "%"}
              />
              <Card
                label="Độ phủ"
                value={pct(s.minimum_coverage)}
                note={fmt(s.pairs_per_route) + " cửa sổ / tuyến"}
              />
              <Card
                label="Tiêu chí"
                value="Tổng 30"
                note="M05 · origin hằng ngày"
              />
            </div>
            <p className="caption">
              Test hồi cứu, không phải holdout độc lập. Hướng tinh chỉnh từng
              được chọn sau khi xem test. 63 cửa sổ chồng nhau không phải 63 mẫu
              độc lập; actual0 vẫn vào MAE/WAPE/bias. Tổng kết top10 không đổi
              theo bộ lọc.
            </p>
          </>
        )}
        <Panel
          title="Sai số dự báo lịch sử"
          note="Metric toàn kỳ test đủ nhãn; không phụ thuộc ngày lập đang xem."
          action={
            <select
              aria-label="Nhịp chấm tổng 30"
              value={cadence}
              onChange={(e) => setCadence(e.target.value)}
            >
              <option value="daily_origins">Origin hằng ngày</option>
              <option value="nonoverlapping_30d">Cửa sổ không chồng</option>
            </select>
          }
        >
          <State loading={metrics.loading} error={metrics.error} />
          <Table
            rows={metrics.data?.items ?? []}
            columns={[
              { key: "destination_country", label: "Quốc gia" },
              { key: "carrier", label: "Nhà mạng" },
              { key: "mape_positive_pct", label: "MAPE (%)" },
              { key: "mae", label: "MAE" },
              { key: "wape_pct", label: "WAPE (%)" },
              { key: "bias", label: "Bias" },
              { key: "coverage", label: "Độ phủ", render: pct },
              { key: "n_scored_pairs", label: "Cửa sổ" },
            ]}
          />
          {base && (
            <ExportButton
              url={`${base}/exports/monthly_metrics?${scope}&split=test&cadence=${cadence}`}
            />
          )}
        </Panel>
        {s && (
          <Panel title="Đối chiếu baseline · toàn bộ top 10">
            <Table
              rows={s.baselines}
              columns={[
                { key: "model", label: "Phương pháp" },
                { key: "mean_mape_positive_pct", label: "MAPE (%)" },
                { key: "routes_below_20_pct", label: "Số tuyến ≤20%" },
              ]}
            />
          </Panel>
        )}
        {benchmark && (
          <p className="caption">
            Nguồn {String(benchmark.benchmark_run_id)} · gói{" "}
            {String(benchmark.benchmark_package_id).slice(0, 12)} ·{" "}
            {String(benchmark.acceptance_version)}. Forecast tồn H14 là luồng
            riêng của phương án.
          </p>
        )}
      </details>
    </>
  );
}
