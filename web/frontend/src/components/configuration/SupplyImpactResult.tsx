import type { Row, Run, WorkspaceData } from "../../types/api";
import type { Context } from "../../types/context";
import { useResource } from "../../hooks/useResource";
import { resultQuery } from "../../utils/url";
import { State } from "../ui/State";
import { Panel } from "../ui/Panel";
import { fmt, text } from "../../utils/format";
import { warehouseName } from "../../utils/warehouse";
import { capLabel, internalLabel, providerLabel } from "../../utils/trade";

export function SupplyImpactTab({ run, ctx, onItem }: {
  run: Run; ctx: Context; onItem: (row: Row, page?: string) => void;
}) {
  const resource = useResource<WorkspaceData>(ctx.origin
    ? `/runs/${run.id}/workspace?${resultQuery(ctx, { as_of_date: ctx.origin })}` : null);
  return <>
    <State loading={resource.loading} error={resource.error} />
    {!resource.loading && !resource.error && (resource.data?.supply_impacts
      ? <SupplyImpactResult impacts={resource.data.supply_impacts} date={ctx.origin} onItem={onItem} />
      : <p className="notice">Lượt chạy này chưa có dữ liệu ảnh hưởng ngừng cung cấp tại ngày đang chọn.</p>)}
  </>;
}

export function SupplyImpactResult({ impacts, date, onItem }: {
  impacts: WorkspaceData["supply_impacts"];
  date: string;
  onItem: (row: Row, page?: string) => void;
}) {
  if (!impacts) return null;
  return <Panel title="Ảnh hưởng ngừng cung cấp" note={`Số liệu ngày ${date} · UTC, lấy từ lượt chạy và bộ lọc đang xem. Mỗi nhóm hiển thị một mặt hàng; chọn mã hàng ở bộ lọc để xem mặt hàng khác.`}>
    <div className="supply-impact-grid">
      {(["internal", "provider"] as const).map(kind => {
        const group = impacts[kind];
        const row = group.item;
        return <article className="supply-impact-card" key={kind}>
          <h3>{kind === "internal" ? "Ngừng nhập nội bộ" : "Ngừng cung cấp từ nhà mạng"}</h3>
          {!row ? <p className="muted">Không có mặt hàng thuộc nhóm này tại ngày và bộ lọc đang xem.</p> : <>
            <div className="supply-impact-product">
              <button className="text-button" onClick={() => onItem(row, "inventory")}>{text(row.sku)}</button>
              <span>{text(row.product_type)} · {text(row.carrier)} · {warehouseName(row)}</span>
              <small>Đang hiển thị 1/{fmt(group.total)} mặt hàng · cửa sổ {text(row.window_origin)}</small>
            </div>
            <p className="supply-impact-status">{kind === "internal" ? internalLabel(row.internal_status) : providerLabel(row.provider_status)}</p>
            <p>Nhập mới: <strong>{row.replenishment_allowed === true ? "Được phép" : row.replenishment_allowed === false ? "Bị chặn" : "Chưa xác định"}</strong> · Bán: <strong>{row.sales_allowed === true ? "Được phép" : row.sales_allowed === false ? "Bị chặn" : "Chưa xác định"}</strong></p>
            <dl className="supply-impact-metrics">
              {[["Tồn cuối ngày", "total_qty"], ["Tồn được bán", "sellable_qty"], ["Tồn bị chặn bán", "blocked_qty"], ["Hàng đang về", "pending_qty"]].map(([title, field]) => <div key={field}><dt>{title}</dt><dd>{fmt(row[field])}</dd></div>)}
            </dl>
            <div className="supply-impact-order">
              <span>Đề xuất theo chính sách → nhập cuối cùng</span>
              <strong>{fmt(row.q_policy)} → {fmt(row.q_final)} đơn vị</strong>
              <span>{capLabel(row.cap_reason)}</span>
            </div>
            <details>
              <summary>Xem số liệu trong ngày và ngưỡng nhập</summary>
              <dl className="supply-impact-metrics">
                {[["Hàng đã về trong ngày", "receipts_qty"], ["Nhu cầu nguồn", "source_sales_qty"], ["Đã đáp ứng", "fulfilled_qty"], ["Nhu cầu bị chặn bán", "actual_blocked_qty"], ["Thiếu hàng được phép bán", "shortage_qty"], ["SS · tồn an toàn", "ss"], ["ROP · ngưỡng nhập", "rop"], ["IP · tồn + đang về", "inventory_position"]].map(([title, field]) => <div key={field}><dt>{title}</dt><dd>{fmt(row[field])}</dd></div>)}
              </dl>
              <p className="muted">Nhu cầu bị chặn bán được tách khỏi thiếu hàng. Lô đã đặt vẫn theo sổ tồn của lượt chạy; lịch ngừng không tự hủy lô.</p>
              {row.quantity_diagnostics_available === false && <p className="muted">Dấu —: lượt chạy không lưu đủ chẩn đoán lượng nhập cho ngày này.</p>}
            </details>
          </>}
        </article>;
      })}
    </div>
  </Panel>;
}
