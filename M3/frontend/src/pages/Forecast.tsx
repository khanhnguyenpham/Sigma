import { useEffect, useState } from "react";
import { MonthlyForecast } from "../components/MonthlyForecast";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import {
  useResource,
  Panel,
  State,
  Table,
  Pager,
  ExportButton,
} from "../components/common";
import {
  type Run,
  type Context,
  type Page,
  type Row,
  resultQuery,
  fmt,
} from "../api/client";
export function Forecast({ run, ctx }: { run?: Run; ctx: Context }) {
  const [mode, setMode] = useState<"monthly" | "operational">("monthly");
  const [daily, setDaily] = useState(false),
    [block, setBlock] = useState("1"),
    [page, setPage] = useState(1);
  const id = run?.kind === "forecast" ? run.id : run?.forecast_run_id;
  const ready = !!id && run?.status === "complete";
  useEffect(
    () => setPage(1),
    [
      ctx.runId,
      ctx.origin,
      ctx.warehouseId,
      ctx.itemId,
      ctx.productType,
      block,
    ],
  );
  const q = resultQuery(
    {
      ...ctx,
      supplierId: "",
      itemId: daily ? ctx.itemId : "",
      productType: daily ? ctx.productType : "",
    },
    {
      as_of_date: ctx.origin,
      page,
      page_size: 50,
      block: daily ? undefined : block,
    },
  );
  const route = useResource<Page>(
    ready && mode === "operational"
      ? `/runs/${id}/forecasts/${daily ? "items" : "routes"}?${q}${daily ? "&aggregate=route_day" : ""}`
      : null,
  );
  const metrics = useResource<Page>(
    ready && mode === "operational"
      ? `/runs/${id}/metrics?${resultQuery({ ...ctx, itemId: "", supplierId: "", productType: "" }, { block, cadence: "daily_origins", granularity: daily ? "allocated_daily" : "weekly", page_size: 100 })}`
      : null,
  );
  const rows = route.data?.items ?? [];
  const test = metrics.data?.items.filter((r) => r.split === "test") ?? [];
  return (
    <>
      <div className="page-intro">
        <span className="eyebrow">01 / NHU CẦU</span>
        <h1>Dự báo theo tuyến</h1>
        <p>
          Tổng 30 ngày là tiêu chí chính R05 theo M05. Tổng tuần và ngày phân bổ
          phục vụ vận hành tồn kho H14.
        </p>
      </div>
      <div className="segments" aria-label="Phạm vi dự báo">
        <button
          className={mode === "monthly" ? "active" : ""}
          onClick={() => setMode("monthly")}
        >
          Tổng 30 · R05
        </button>
        <button
          className={mode === "operational" ? "active" : ""}
          onClick={() => setMode("operational")}
        >
          Vận hành · Tổng 7 / ngày
        </button>
      </div>
      {mode === "monthly" ? (
        <MonthlyForecast run={run} ctx={ctx} />
      ) : !ready ? (
        <div className="notice">
          Chọn một lượt dự báo hoặc mô phỏng đã hoàn tất để xem kết quả.
        </div>
      ) : (
        <>
          <Panel
            title={
              daily
                ? "Ngày phân bổ từ tổng tuần"
                : "Hai tổng tuần không chồng lấp"
            }
            note={`Origin ${ctx.origin} · D+1…D+7 / D+8…D+14`}
            action={
              <div className="segments">
                <button
                  className={!daily ? "active" : ""}
                  onClick={() => {
                    setDaily(false);
                    setPage(1);
                  }}
                >
                  Tổng 7
                </button>
                <button
                  className={daily ? "active" : ""}
                  onClick={() => {
                    setDaily(true);
                    setPage(1);
                  }}
                >
                  Ngày phân bổ
                </button>
              </div>
            }
          >
            <State
              loading={route.loading}
              error={route.error}
              empty={!route.loading && !route.error && !rows.length}
            />
            {!daily && (ctx.itemId || ctx.productType) && (
              <p className="caption">
                Tổng tuần hiển thị toàn tuyến; SKU/loại chỉ áp dụng khi chuyển
                sang Ngày phân bổ.
              </p>
            )}
            {rows.length > 0 && (
              <>
                {daily ? (
                  ctx.warehouseId ? (
                    <div className="chart">
                      <ResponsiveContainer width="100%" height={260}>
                        <LineChart data={rows}>
                          <CartesianGrid
                            strokeDasharray="3 3"
                            vertical={false}
                          />
                          <XAxis
                            dataKey="target_date"
                            tick={{ fontSize: 11 }}
                          />
                          <YAxis />
                          <Tooltip />
                          <Legend />
                          <Line
                            dataKey="forecast_qty"
                            name="Dự báo phân bổ"
                            stroke="#087e86"
                            dot={false}
                          />
                          <Line
                            dataKey="actual_qty"
                            name="Actual"
                            stroke="#d39448"
                            connectNulls={false}
                            dot={false}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <p className="caption">
                      Chọn một kho để xem đường dự báo 14 ngày; bảng bên dưới
                      vẫn gồm các kho trong phạm vi lọc.
                    </p>
                  )
                ) : (
                  <>
                    <p className="caption">
                      Biểu đồ minh họa tối đa 12 dòng đầu trang theo thứ tự
                      bảng; xem đầy đủ trong bảng hoặc CSV.
                    </p>
                    <div className="chart">
                      <ResponsiveContainer width="100%" height={260}>
                        <BarChart
                          data={rows.slice(0, 12).map((r) => ({
                            ...r,
                            route_label:
                              String(r.destination_country) +
                              " / " +
                              String(r.carrier),
                          }))}
                        >
                          <CartesianGrid
                            strokeDasharray="3 3"
                            vertical={false}
                          />
                          <XAxis
                            dataKey="route_label"
                            tick={{ fontSize: 10 }}
                          />
                          <YAxis />
                          <Tooltip />
                          <Legend />
                          <Bar
                            dataKey="forecast_qty"
                            name="Dự báo tuần"
                            fill="#087e86"
                          />
                          <Bar
                            dataKey="actual_qty"
                            name="Actual"
                            fill="#d39448"
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </>
                )}
                <Table
                  rows={rows}
                  columns={[
                    { key: "destination_country", label: "Điểm đến" },
                    { key: "carrier", label: "Nhà mạng" },
                    { key: "target_date", label: "Ngày kết thúc / ngày" },
                    { key: "block", label: "Khối" },
                    { key: "forecast_qty", label: "Dự báo" },
                    { key: "actual_qty", label: "Actual" },
                    {
                      key: "model_id",
                      label: "Mô hình",
                      render: (v) =>
                        daily ? "Phân bổ tổng tuần" : String(v ?? "—"),
                    },
                  ]}
                />
                <Pager
                  page={page}
                  total={route.data?.total ?? 0}
                  onChange={setPage}
                />
                <ExportButton
                  url={`/runs/${id}/exports/${daily ? "item_forecasts" : "route_forecasts"}?${q}${daily ? "&aggregate=route_day" : ""}`}
                />
              </>
            )}
          </Panel>
          <Panel
            title={
              daily
                ? "Sai số ngày phân bổ · test lịch sử"
                : "Sai số tổng tuần · test lịch sử"
            }
            note="Metric toàn bộ các cửa sổ test đủ nhãn, không chỉ origin đang vẽ. H1–7 và H8–14 chấm riêng."
            action={
              <select
                aria-label="Khối đánh giá"
                value={block}
                onChange={(e) => setBlock(e.target.value)}
              >
                <option value="1">H1–7</option>
                <option value="2">H8–14</option>
              </select>
            }
          >
            <State loading={metrics.loading} error={metrics.error} />
            <Table
              rows={test}
              columns={[
                { key: "destination_country", label: "Điểm đến" },
                { key: "carrier", label: "Nhà mạng" },
                { key: "mape_positive_pct", label: "MAPE (%)" },
                { key: "mae", label: "MAE" },
                { key: "wape_pct", label: "WAPE (%)" },
                { key: "bias", label: "Bias có dấu" },
                {
                  key: "coverage",
                  label: "Độ phủ",
                  render: (v) =>
                    typeof v === "number" ? fmt(v * 100, 1) + "%" : "—",
                },
                { key: "n_scored_pairs", label: "Cặp chấm" },
              ]}
            />
            <p className="caption">
              MAPE chỉ trên actual dương. Ngày phân bổ là dự báo dẫn xuất. Theo
              M05, R05 chấm tổng 30 ngày ở tab riêng; các bảng này là chẩn đoán
              vận hành H14.
            </p>
          </Panel>
        </>
      )}
    </>
  );
}
