import { InventoryDetails } from "../components/inventory/InventoryDetails";
import { useEffect, useState } from "react";
import { type Run, type Page, type Row } from "../types/api";
import { type Context } from "../types/context";
import { resultQuery } from "../utils/url";
import { fmt, text } from "../utils/format";
import { useResource } from "../hooks/useResource";
import { Panel } from "../components/ui/Panel";
import { Table } from "../components/ui/Table";
import { Pager } from "../components/ui/Pager";
import { State } from "../components/ui/State";
import { ExportButton } from "../components/ui/ExportButton";
import { Card } from "../components/ui/Card";

import { PlanRequired } from "../components/ui/PlanRequired";
import { badge } from "../components/ui/Badge";
import type { PurchasingView } from "../types/context";
import { Icon } from "../components/ui/Icon";
import type { WorkspaceData } from "../types/api";
export function Inventory({
  run,
  ctx,
  onChoose,
  onItem,
}: {
  run?: Run;
  ctx: Context;
  onChoose?: () => void;
  onItem?: (row: Row, page?: string, view?: PurchasingView) => void;
}) {
  const [page, setPage] = useState(1),
    [status, setStatus] = useState(""),
    [selection, setSelection] = useState<{ key: string; row: Row }>();
  const key = JSON.stringify([ctx, status]);
  const focused = selection?.key === key ? selection.row : undefined;
  useEffect(() => setPage(1), [key]);
  const ready =
    run?.status === "complete" &&
    run.result_summary.inventory_available !== false &&
    ["policy_replay", "alert_replay", "stock_projection"].includes(run.kind);
  const q = resultQuery(ctx, {
    date_from: ctx.origin,
    date_to: ctx.origin,
    page,
    page_size: 50,
    state: status,
  });
  const data = useResource<Page>(
    ready ? `/runs/${run.id}/inventory?${q}` : null,
  );
  const summary = useResource<WorkspaceData>(
    ready && ctx.origin
      ? `/runs/${run.id}/workspace?${resultQuery(ctx, { as_of_date: ctx.origin })}`
      : null,
  );
  const s = summary.data?.summary;
  const rows = data.data?.items ?? [];
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Tồn kho</h1>
          <p>
            Theo dõi từng mã SIM/gói data, so tồn hiện có với ngưỡng nhập và
            lượng hàng đang về.
          </p>
        </div>
        {ready && (
          <ExportButton url={`/runs/${run.id}/exports/inventory_daily?${q}`} />
        )}
      </div>
      {!ready ? (
        <PlanRequired onChoose={onChoose} />
      ) : (
        <>
          <div className="stats">
            <Card
              label="Mặt hàng đang quản lý"
              value={fmt(s?.item_count)}
              note="Theo kho, SKU và ngày đang chọn"
              icon="box"
            />
            <Card
              label="Tồn hiện có"
              value={fmt(s?.on_hand_units)}
              note="Chưa cộng lượng đang về"
              icon="grid"
            />
            <Card
              label="Dưới ngưỡng tồn"
              value={fmt(s?.low_stock_items)}
              note="Bao gồm các mặt hàng đã đặt đủ"
              icon="alert"
              tone="orange"
            />
            <Card
              label="Cần đặt thêm"
              value={fmt(s?.replenish_items)}
              note="Lượng đề xuất lớn hơn 0"
              icon="truck"
              tone="teal"
            />
          </div>
          <State loading={summary.loading} error={summary.error} />
          <Panel
            title="Danh sách tồn kho"
            note={`Ngày ${ctx.origin} · Nhấn một mặt hàng để xem chi tiết.`}
            action={
              <select
                aria-label="Trạng thái tồn kho"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="">Tất cả trạng thái</option>
                <option value="low_stock">Cần đặt thêm</option>
                <option value="pending_covers">Đã có đủ hàng đang về</option>
              </select>
            }
          >
            <State
              loading={data.loading}
              error={data.error}
              empty={!data.loading && !data.error && !rows.length}
            />
            {!data.loading && !data.error && rows.length > 0 && (
              <Table
                rows={rows}
                onRow={(row) => setSelection({ key, row })}
                columns={[
                  {
                    key: "sku",
                    label: "Mặt hàng",
                    render: (v, r) => (
                      <div className="cell-product">
                        <strong>{String(v)}</strong>
                        <small>{String(r.product_type)}</small>
                      </div>
                    ),
                  },
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
                  { key: "closing_qty", label: "Tồn hiện có" },
                  { key: "rop", label: "Ngưỡng nhập" },
                  { key: "pending_qty", label: "Đang về" },
                  {
                    key: "recommended_qty",
                    label: "Cần đặt",
                    render: (v) => (
                      <span className="quantity-emphasis">{fmt(v)}</span>
                    ),
                  },
                  {
                    key: "needs_replenishment",
                    label: "Trạng thái",
                    render: (v, r) =>
                      badge(
                        v
                          ? Number(r.recommended_qty) > 0
                            ? "low_stock"
                            : "pending_covers"
                          : "sufficient",
                      ),
                  },
                  {
                    key: "item_id",
                    label: "",
                    render: () => <Icon name="chevron" size={15} />,
                  },
                ]}
              />
            )}
            <Pager
              page={page}
              total={data.data?.total ?? 0}
              onChange={setPage}
            />
          </Panel>
          {run.kind === "stock_projection" && (
            <p className="caption">
              Số tồn tại mốc chốt được khởi tạo theo phương án mô phỏng. Các
              ngày sau mốc chốt là dự kiến; chưa ghi nhận là tồn thực tế.
            </p>
          )}
        </>
      )}
      {focused && (
        <InventoryDetails
          focused={focused}
          onClose={() => setSelection(undefined)}
          onItem={onItem}
        />
      )}
    </>
  );
}
