import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Context } from "../../types/context";
import type { Page, Run } from "../../types/api";
import { useResource } from "../../hooks/useResource";
import { apiAllPages } from "../../services/http";
import { resultQuery } from "../../utils/url";
import { compareForecast14, forecastDay } from "../../utils/forecastComparison";
import { fmt } from "../../utils/format";
import { Panel } from "../ui/Panel";
import { Card } from "../ui/Card";
import { State } from "../ui/State";
import { Table } from "../ui/Table";
import { Pager } from "../ui/Pager";
import { ExportButton } from "../ui/ExportButton";

export function ForecastComparison({ run, ctx }: { run: Run; ctx: Context }) {
  const [selectedDay, setSelectedDay] = useState("");
  const [page, setPage] = useState(1);
  useEffect(() => setPage(1), [ctx.warehouseId, ctx.itemId, ctx.productType]);
  const origins = useResource<Page<{ as_of_date: string; actual_available: boolean }>>(`/runs/${run.id}/forecasts/origins`);
  const forecastId = run.kind === "forecast" ? run.id : run.forecast_run_id;
  const days = origins.data?.items ?? [];
  const day = days.some(row => row.as_of_date === selectedDay) ? selectedDay
    : days.some(row => row.as_of_date === ctx.origin) ? ctx.origin : days.at(-1)?.as_of_date ?? "";
  const daily = !!(ctx.itemId || ctx.productType);
  const query = resultQuery({ ...ctx, warehouseId: ctx.warehouseScope === "receiving" ? "" : ctx.warehouseId,
    warehouseScope: undefined, supplierId: "", internalStatus: undefined, providerStatus: undefined,
    replenishmentAllowed: undefined, salesAllowed: undefined, windowOrigin: undefined },
  { as_of_date: day, page_size: 100, ...(daily ? { aggregate: "route_day" } : {}) });
  const path = `/runs/${run.id}/forecasts/${daily ? "items" : "routes"}?${query}`;
  const results = useResource<Page>(day ? path : null, false, 0, apiAllPages);
  const rows = results.data?.items ?? [];
  const complete = !!results.data && rows.length === results.data.total;
  const comparison = day && complete ? compareForecast14(rows, day, daily) : undefined;
  const missing = (value: unknown) => typeof value === "number" ? fmt(value, 2) : "Chưa đủ dữ liệu";
  const viewPage = Math.min(page, Math.max(1, Math.ceil((comparison?.items.length ?? 0) / 50)));
  return <Panel title="So sánh dự báo và thực tế 14 ngày"
    note="Đối chiếu nhu cầu dự báo với lượng bán nguồn đã ghi nhận; không phải lượng bán mô phỏng theo tồn."
    action={<label className="comparison-date">Ngày đánh giá · UTC
      <select aria-label="Ngày đánh giá dự báo UTC" value={day} disabled={origins.loading || !!origins.error || !days.length}
        onChange={event => { setSelectedDay(event.target.value); setPage(1); }}>
        {!days.length && <option value="">Chưa có mốc dự báo</option>}
        {days.map(row => <option key={row.as_of_date} value={row.as_of_date}>{row.as_of_date.split("-").reverse().join("/")}</option>)}
      </select>
    </label>}>
    <p className="caption">Ngày đánh giá chỉ đổi cửa sổ so sánh, không thay ngày số liệu tồn kho hoặc chạy lại mô hình. So sánh theo tuyến nguồn và sản phẩm; bộ lọc kho nhận và quyền mua bán không áp dụng tại đây.</p>
    {day && <p className="comparison-window">Dự báo lập tại <strong>{day}</strong> · So sánh từ <strong>{forecastDay(day, 1)}</strong> đến <strong>{forecastDay(day, 14)}</strong> (D+1…D+14).</p>}
    <State loading={origins.loading || results.loading} error={origins.error ?? results.error} />
    {!origins.loading && !origins.error && !days.length && <p className="notice">Dự báo cha chưa có mốc đánh giá được lưu.</p>}
    {results.data && !complete && <p className="notice">Chưa tải đủ dữ liệu để cộng tổng 14 ngày. Hãy tải lại.</p>}
    {comparison && !results.loading && !results.error && <>
      {!comparison.items.length ? <p className="notice">Không có dự báo trong phạm vi đang chọn tại mốc này.</p> : <>
        <div className="stats comparison-stats">
          <Card label="Dự báo 14 ngày" value={missing(comparison.forecast)} note="Tổng lượng nhu cầu dự báo" />
          <Card label="Bán thực tế 14 ngày" value={comparison.actual === null ? "Chưa đủ thực tế" : fmt(comparison.actual, 2)} note={`${comparison.actualRoutes}/${comparison.items.length} tuyến đủ thực tế cả 14 ngày`} />
          <Card label="Chênh lệch dự báo − thực tế" value={missing(comparison.difference)} note="Dương: dự báo cao hơn; âm: dự báo thấp hơn" />
        </div>
        {comparison.actual === null && <p className="notice">Chưa đủ dữ liệu thực tế cho toàn bộ 14 ngày trong phạm vi này. Phần thiếu được để trống, không tính thành 0.</p>}
        <p className="caption">Biểu đồ hiển thị tối đa 12 tuyến đầu; tổng phía trên gồm toàn bộ phạm vi, không chỉ trang bảng đang xem.</p>
        <div className="chart"><ResponsiveContainer width="100%" height={260}><BarChart data={comparison.items.slice(0, 12)}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="carrier" tick={{ fontSize: 10 }} /><YAxis /><Tooltip /><Legend />
          <Bar dataKey="forecast_qty" name="Dự báo 14 ngày" fill="#5366df" /><Bar dataKey="actual_qty" name="Bán thực tế 14 ngày" fill="#299581" />
        </BarChart></ResponsiveContainer></div>
        <Table rows={comparison.items.slice((viewPage - 1) * 50, viewPage * 50)} columns={[
          { key: "destination_country", label: "Thị trường" }, { key: "carrier", label: "Nhà mạng" },
          { key: "forecast_qty", label: "Dự báo 14 ngày", render: missing },
          { key: "actual_qty", label: "Bán thực tế 14 ngày", render: missing },
          { key: "difference_qty", label: "Dự báo − thực tế", render: missing },
        ]} />
        <Pager page={viewPage} total={comparison.items.length} onChange={setPage} />
        {forecastId && <ExportButton url={`/runs/${forecastId}/exports/${daily ? "item_forecasts" : "route_forecasts"}?${query}`} />}
      </>}
    </>}
  </Panel>;
}
