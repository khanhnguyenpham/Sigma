import { useEffect, useState } from "react";
import {
  type Run,
  type Context,
  type Page,
  type Row,
  resultQuery,
  fmt,
  text,
} from "../api/client";
import {
  useResource,
  Panel,
  Table,
  Pager,
  State,
  ExportButton,
  Card,
} from "../components/common";
export function Inventory({ run, ctx }: { run?: Run; ctx: Context }) {
  const [page, setPage] = useState(1),
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
  ]);
  const ready =
    run?.status === "complete" &&
    ["policy_replay", "alert_replay", "stock_projection"].includes(run.kind);
  const q = resultQuery(ctx, {
    date_from: ctx.origin,
    date_to: ctx.origin,
    page,
    page_size: 50,
  });
  const resource = useResource<Page>(
    ready ? `/runs/${run.id}/inventory?${q}` : null,
  );
  const rows = resource.data?.items ?? [];
  return (
    <>
      <div className="page-intro">
        <span className="eyebrow">02 / TỒN & NGƯỠNG</span>
        <h1>Từng mặt hàng, từng quyết định.</h1>
        <p>
          Tồn, lượng đã đặt và ngưỡng được lấy từ cùng snapshot policy. Nhấn một
          dòng để xem cách tính.
        </p>
      </div>
      {!ready ? (
        <div className="notice">
          Chọn lượt mô phỏng chính sách, đánh giá cảnh báo hoặc ảnh chụp tồn kho
          đã hoàn tất.
        </div>
      ) : (
        <Panel
          title={`Sổ tồn · ${ctx.origin}`}
          note="Tồn đầu + nhận − đáp ứng = tồn cuối. Số bán = đáp ứng + thiếu."
          action={
            <ExportButton
              url={`/runs/${run.id}/exports/inventory_daily?${q}`}
            />
          }
        >
          {run.kind === "stock_projection" && (
            <p className="caption">
              Dòng tại mốc chốt là khởi tạo tồn mô phỏng từ 28 ngày trước đó;
              các cột bán/đáp ứng/thiếu bằng 0 ở dòng khởi tạo, không phải
              actual bán của ngày này. 14 ngày sau chỉ có projection.
            </p>
          )}
          <State
            loading={resource.loading}
            error={resource.error}
            empty={!resource.loading && !resource.error && !rows.length}
          />
          <Table
            rows={rows}
            onRow={setFocused}
            columns={[
              { key: "carrier", label: "Nhà mạng" },
              { key: "sku", label: "SKU" },
              { key: "product_type", label: "Loại" },
              { key: "opening_qty", label: "Đầu" },
              { key: "receipts_qty", label: "Nhận" },
              { key: "sales_qty", label: "Bán" },
              { key: "fulfilled_qty", label: "Đáp ứng" },
              { key: "shortage_qty", label: "Thiếu" },
              { key: "closing_qty", label: "Cuối" },
              { key: "rop", label: "ROP" },
              { key: "pending_qty", label: "Đang về" },
              { key: "recommended_qty", label: "Đề xuất Q" },
            ]}
          />
          <Pager
            page={page}
            total={resource.data?.total ?? 0}
            onChange={setPage}
          />
        </Panel>
      )}
      {focused && (
        <Panel
          title={`${text(focused.sku)} · Giải thích đề xuất`}
          note="L7 / R1 / H14 · thời gian nhập khác lịch giao khách."
        >
          <div className="stats">
            <Card label="Safety stock" value={fmt(focused.ss)} />
            <Card
              label="ROP forecast / floor"
              value={`${fmt(focused.rop_forecast)} / ${fmt(focused.configured_rop_floor)}`}
            />
            <Card label="ROP đã áp dụng" value={fmt(focused.rop)} tone="teal" />
            <Card
              label="Lượng đề xuất"
              value={fmt(focused.recommended_qty)}
              tone="orange"
            />
          </div>
          <div className="formula">
            <span>ROP = max(ROP forecast, floor)</span>
            <span>S = ROP + ceil(f8) = {fmt(focused.target_stock)}</span>
            <span>
              IP = tồn cuối + đang về = {fmt(focused.inventory_position)}
            </span>
            <span>
              MOQ = {fmt(focused.moq)} · policy v{text(focused.policy_version)}
            </span>
          </div>
          <p className="caption">
            Chỉ trigger khi tồn cuối &lt; ROP. Pending đủ có thể làm Q = 0 dù
            vẫn dưới ngưỡng. IP chưa cộng Q vừa đề xuất.
          </p>
        </Panel>
      )}
    </>
  );
}
