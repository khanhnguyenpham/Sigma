import { useState } from "react";
import { type Run, type Context, type Page, resultQuery } from "../api/client";
import {
  useResource,
  Panel,
  State,
  Table,
  Pager,
  ExportButton,
  badge,
} from "../components/common";
export function Replenishment({ run, ctx }: { run?: Run; ctx: Context }) {
  const [lots, setLots] = useState(false),
    [page, setPage] = useState(1);
  const ready =
    run?.status === "complete" &&
    ["policy_replay", "alert_replay", "stock_projection"].includes(run.kind);
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
        <span className="eyebrow">03 / BỔ SUNG HÀNG</span>
        <h1>Đặt đúng lượng, hiểu rõ ETA.</h1>
        <p>
          Đề xuất và lô mô phỏng được tách riêng. Các thao tác không gửi đơn đến
          supplier thật.
        </p>
      </div>
      {!ready ? (
        <div className="notice">Chọn một lượt tồn kho đã hoàn tất.</div>
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
              : "Lượng đặt theo IP và MOQ; các ca pending đủ có Q0 xem ở Tồn kho."
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
                Khuyến nghị
              </button>
              <button
                className={lots ? "active" : ""}
                onClick={() => {
                  setLots(true);
                  setPage(1);
                }}
              >
                Các lô nhập
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
                    { key: "eta", label: "ETA" },
                    { key: "ordered_qty", label: "Lượng đặt" },
                    { key: "received_qty", label: "Đã nhận" },
                    { key: "status", label: "Trạng thái", render: badge },
                  ]
                : [
                    { key: "carrier", label: "Nhà mạng" },
                    { key: "sku", label: "SKU" },
                    { key: "closing_qty", label: "Tồn cuối" },
                    { key: "rop", label: "ROP" },
                    { key: "inventory_position", label: "IP trước Q" },
                    { key: "moq", label: "MOQ" },
                    { key: "recommended_qty", label: "Đề xuất Q" },
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
