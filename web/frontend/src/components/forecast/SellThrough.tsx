import { useEffect, useState } from "react";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";
import type { Context } from "../../types/context";
import type { Page } from "../../types/api";
import { useResource } from "../../hooks/useResource";
import { resultQuery } from "../../utils/url";
import { Panel } from "../ui/Panel";
import { State } from "../ui/State";
import { Table } from "../ui/Table";
import { Pager } from "../ui/Pager";
import { ExportButton } from "../ui/ExportButton";
import { badge } from "../ui/Badge";

export function SellThrough({ runId, ctx }: { runId: string; ctx: Context }) {
  const [page, setPage] = useState(1);
  useEffect(() => setPage(1), [runId, ctx.origin, ctx.itemId, ctx.warehouseId, ctx.productType, ctx.supplierId]);
  const q = resultQuery(ctx, { as_of_date: ctx.origin, page, page_size: 50, aggregate: ctx.itemId ? undefined : "route_day" });
  const data = useResource<Page>(ctx.origin ? `/runs/${runId}/sell-through?${q}` : null);
  const rows = data.data?.items ?? [];
  return <Panel title="Dự kiến bán theo tồn" note={`Kế hoạch đã lưu · ngày lập ${ctx.origin || "chưa chọn"} UTC. Chỉ tính tồn và lô đã biết, không thêm lô vừa đề xuất.`}>
    {!ctx.origin && <p className="notice">Chọn ngày lập kế hoạch để xem dự kiến bán theo tồn.</p>}
    <State loading={data.loading} error={data.error} empty={!data.loading && !data.error && !!ctx.origin && !rows.length} />
    {rows.length > 0 && <>
      {(ctx.warehouseId || ctx.itemId) && <div className="chart"><ResponsiveContainer width="100%" height={250}><LineChart data={rows}>
        <CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="target_date" /><YAxis /><Tooltip /><Legend />
        <Line dataKey="projected_sales_qty" name="Dự kiến bán" stroke="#5366df" dot={false} />
        <Line dataKey="closing_forecast" name="Tồn dự kiến" stroke="#299581" dot={false} />
      </LineChart></ResponsiveContainer></div>}
      <Table rows={rows} columns={[
        {key:"target_date",label:"Ngày UTC"},{key:"sku",label:"Sản phẩm"},{key:"city",label:"Kho"},
        {key:"projected_sales_qty",label:"Dự kiến bán"},{key:"receipts_qty",label:"Hàng về đã biết"},
        {key:"closing_forecast",label:"Tồn cuối ngày"},{key:"supply_status",label:"Cung cấp",render:(v) => v ? badge(v) : "Theo từng sản phẩm"},
      ]} /><Pager page={page} total={data.data?.total ?? 0} onChange={setPage} />
      <ExportButton url={`/runs/${runId}/exports/sell_through?${q}`} />
      <details className="advanced-section"><summary>Nhu cầu dự báo và phần chưa đáp ứng</summary><Table rows={rows} columns={[
        {key:"target_date",label:"Ngày UTC"},{key:"forecast_demand_qty",label:"Nhu cầu dự báo"},
        {key:"projected_sales_qty",label:"Có thể bán"},{key:"unserved_demand_qty",label:"Chưa đáp ứng"},
      ]} /><p className="caption">Dự kiến bán có thể thấp hơn nhu cầu. Số liệu là mô phỏng, không phải lượng bán thực tế.</p></details>
    </>}
  </Panel>;
}
