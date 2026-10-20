import { useEffect, useState } from "react";
import { type Run, type Context, type Page, resultQuery } from "../api/client";
import {
  useResource,
  Panel,
  State,
  Table,
  Pager,
  ExportButton,
  badge,
  PlanRequired,
} from "../components/common";
export function Replenishment({
  run,
  ctx,
  onChoose,
}: {
  run?: Run;
  ctx: Context;
  onChoose?: () => void;
}) {
  const [lots, setLots] = useState(false),
    [page, setPage] = useState(1);
  const ready =
    run?.status === "complete" &&
    ["policy_replay", "alert_replay", "stock_projection"].includes(run.kind);
  useEffect(
    () => setPage(1),
    [
      ctx.runId,
      ctx.origin,
      ctx.warehouseId,
      ctx.itemId,
      ctx.supplierId,
      ctx.productType,
      lots,
    ],
  );
  const q = resultQuery(ctx, {
    page,
    page_size: 50,
    ...(!lots
      ? { date_from: ctx.origin, date_to: ctx.origin, state: "low_stock" }
      : {}),
  });
  const data = useResource<Page>(
    ready
      ? `/runs/${run.id}/${lots ? "replenishments" : "inventory"}?${q}`
      : null,
  );
  const rows = data.data?.items ?? [];
  return (
    <>
      <div className="page-intro">
        <h1>Nhập hàng</h1>
        <p>Theo dõi đề xuất bổ sung và lịch các lô nhập trong phương án.</p>
      </div>
      {!ready ? (
        <PlanRequired onChoose={onChoose} />
      ) : (
        <Panel
          title={
            lots
              ? "Lô nhập trong toàn kỳ"
              : "Khuyến nghị cần đặt tại ngày đang xem"
          }
          note={
            lots
              ? "Trạng thái cuối kỳ mô phỏng. ETA luôn là ngày đặt +7, gồm cuối tuần."
              : "Lượng đặt đã tính hàng đang về và số lượng đặt tối thiểu. Nếu đã có đủ hàng đang về, lượng đặt thêm bằng 0; xem ở Tồn kho."
          }
          action={
            <div className="segments">
              <button
                className={!lots ? "active" : ""}
                onClick={() => {
                  setLots(false);
                  setPage(1);
                }}
              >
                Đề xuất nhập
              </button>
              <button
                className={lots ? "active" : ""}
                onClick={() => {
                  setLots(true);
                  setPage(1);
                }}
              >
                Lô nhập hàng
              </button>
            </div>
          }
        >
          <State
            loading={data.loading}
            error={data.error}
            empty={!data.loading && !data.error && !rows.length}
          />
          <Table
            rows={rows}
            columns={
              lots
                ? [
                    { key: "carrier", label: "Nhà mạng" },
                    { key: "sku", label: "SKU" },
                    { key: "ordered_on", label: "Ngày đặt" },
                    { key: "eta", label: "Dự kiến nhận" },
                    { key: "ordered_qty", label: "Lượng đặt" },
                    { key: "received_qty", label: "Đã nhận" },
                    { key: "status", label: "Trạng thái", render: badge },
                  ]
                : [
                    { key: "carrier", label: "Nhà mạng" },
                    { key: "sku", label: "SKU" },
                    { key: "closing_qty", label: "Tồn cuối" },
                    { key: "rop", label: "Ngưỡng nhập (ROP)" },
                    { key: "inventory_position", label: "Vị thế tồn (IP)" },
                    { key: "moq", label: "Lượng tối thiểu (MOQ)" },
                    { key: "recommended_qty", label: "Lượng đề xuất" },
                    { key: "eta_if_ordered", label: "ETA nếu đặt" },
                  ]
            }
          />
          <Pager page={page} total={data.data?.total ?? 0} onChange={setPage} />
          <ExportButton
            url={`/runs/${run.id}/exports/${lots ? "replenishments" : "inventory_daily"}?${q}`}
          />
        </Panel>
      )}
    </>
  );
}
