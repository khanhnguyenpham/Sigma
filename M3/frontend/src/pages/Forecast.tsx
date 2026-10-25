import { useEffect, useState } from "react";
import { MonthlyForecast } from "../components/forecast/MonthlyForecast";
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
import { useResource } from "../hooks/useResource";
import { Panel } from "../components/ui/Panel";
import { State } from "../components/ui/State";
import { Table } from "../components/ui/Table";
import { Pager } from "../components/ui/Pager";
import { ExportButton } from "../components/ui/ExportButton";
import { type Run, type Page, type Row } from "../types/api";
import { type Context } from "../types/context";
import { resultQuery } from "../utils/url";
import { fmt } from "../utils/format";
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
      ? `/runs/${id}/metrics?${resultQuery({ ...ctx, itemId: "", supplierId: "", productType: "" }, { block, split: "test", cadence: "daily_origins", granularity: daily ? "allocated_daily" : "weekly", page_size: 100 })}`
      : null,
  );
  const rows = route.data?.items ?? [];
  const test = metrics.data?.items.filter((r) => r.split === "test") ?? [];
  return (
    <>
      <div className="page-intro">
        <h1>Dự báo nhu cầu</h1>
        <p>
          Dự báo lượng SIM/gói data bán theo quốc gia và nhà mạng. Tổng 30 ngày
          dùng xem nhu cầu dài hơn; kế hoạch tồn kho dùng dự báo 14 ngày từ hai
          khối tuần.
        </p>
      </div>
      <div className="segments" aria-label="Phạm vi dự báo">
        <button
          className={mode === "monthly" ? "active" : ""}
          onClick={() => setMode("monthly")}
        >
          Tổng 30 ngày
        </button>
        <button
          className={mode === "operational" && !daily ? "active" : ""}
          onClick={() => {
            setMode("operational");
            setDaily(false);
            setPage(1);
          }}
        >
          Tổng 7 ngày
        </button>
        <button
          className={mode === "operational" && daily ? "active" : ""}
          onClick={() => {
            setMode("operational");
            setDaily(true);
            setPage(1);
          }}
        >
          Phân bổ theo ngày
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
            title={daily ? "Ngày phân bổ từ tổng tuần" : "Dự báo tổng tuần"}
            note={`Ngày lập ${ctx.origin} · Nhu cầu trong kỳ đang chọn.`}
            action={
              !daily ? (
                <select
                  aria-label="Tuần dự báo"
                  value={block}
                  onChange={(e) => setBlock(e.target.value)}
                >
                  <option value="1">Tuần 1 · D+1…D+7</option>
                  <option value="2">Tuần 2 · D+8…D+14</option>
                </select>
              ) : undefined
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
                            stroke="#5b6de0"
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
                            fill="#5b6de0"
                          />
                          <Bar
                            dataKey="actual_qty"
                            name="Actual"
                            fill="#bdc8f0"
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
          <details className="advanced-section">
            <summary>Chất lượng dự báo lịch sử</summary>
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
                MAPE chỉ trên actual dương. Ngày phân bổ là dự báo dẫn xuất.
                Theo M05, R05 chấm tổng 30 ngày ở tab riêng; các bảng này là
                chẩn đoán vận hành H14.
              </p>
            </Panel>
          </details>
        </>
      )}
    </>
  );
}
