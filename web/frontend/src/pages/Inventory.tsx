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
import { WarehouseDirectory } from "../components/inventory/WarehouseDirectory";
import { warehouseName } from "../utils/warehouse";
export function Inventory({
  run,
  ctx,
  onChoose,
  onItem,
  catalog,
  itemOptions = [],
  supplierOptions = [],
  onWarehouse,
  onFilterChange,
  onNavigate,
}: {
  run?: Run;
  ctx: Context;
  onChoose?: () => void;
  onItem?: (row: Row, page?: string, view?: PurchasingView) => void;
  catalog?: { data?: Page; loading: boolean; error?: Error };
  itemOptions?: Row[];
  supplierOptions?: Row[];
  onWarehouse?: (id: string) => void;
  onFilterChange?: (patch: Partial<Context>) => void;
  onNavigate?: (page: string) => void;
}) {
  const [page, setPage] = useState(1),
    [status, setStatus] = useState(""),
    [selection, setSelection] = useState<{ key: string; row: Row }>();
  const key = JSON.stringify([ctx, status]);
  const focused = selection?.key === key ? selection.row : undefined;
  useEffect(() => setPage(1), [key]);
  useEffect(() => setStatus(""), [ctx.runId, ctx.warehouseId]);
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
  const insideWarehouse = !!ctx.warehouseId;
  const warehouses = catalog?.data?.items ?? [];
  const warehouse = warehouses.find((w) => String(w.id) === ctx.warehouseId);
  const summaryScope = insideWarehouse ? ctx : { ...ctx, itemId: "", supplierId: "", productType: "" };
  const data = useResource<Page>(
    ready && insideWarehouse ? `/runs/${run.id}/inventory?${q}` : null,
  );
  const summary = useResource<WorkspaceData>(
    ready && ctx.origin
      ? `/runs/${run.id}/workspace?${resultQuery(summaryScope, { as_of_date: ctx.origin })}`
      : null,
  );
  const s = summary.data?.summary;
  const rows = data.data?.items ?? [];
  return (
    <>
      {insideWarehouse && <nav className="warehouse-breadcrumb" aria-label="Đường dẫn kho">
        <button className="text-button" onClick={() => onWarehouse?.("")}><span aria-hidden="true">←</span> Danh sách kho</button>
        <span aria-hidden="true">/</span><span aria-current="page">{warehouseName(warehouse)}</span>
      </nav>}
      <div className="page-heading">
        <div>
          <h1>{insideWarehouse ? warehouseName(warehouse) : "Tồn kho"}</h1>
          <p>
            {insideWarehouse ? `${text(warehouse?.destination_country)} · Xem sản phẩm và tình trạng tồn trong kho.` : "Bắt đầu từ kho đang quản lý, sau đó chọn kho để xem sản phẩm bên trong."}
          </p>
          {insideWarehouse && warehouse && <span className="carrier-chip">Nhà mạng <strong>{String(warehouse.carrier)}</strong></span>}
        </div>
        {ready && insideWarehouse && <div className="warehouse-actions">
          {onNavigate && <><button onClick={() => onNavigate("forecast")}><Icon name="chart" size={16} /> Dự báo nhu cầu</button>
            <button onClick={() => onNavigate("replenishment")}><Icon name="truck" size={16} /> Nhập hàng</button></>}
          <ExportButton url={`/runs/${run.id}/exports/inventory_daily?${q}`} />
        </div>}
      </div>
      {!ready ? (
        <PlanRequired onChoose={onChoose} />
      ) : (
        <>
          {!insideWarehouse ? <div className="stats">
            <Card label="Kho đang quản lý" value={catalog?.data ? fmt(warehouses.length) : "—"} note="Mỗi kho đặt tại một thành phố" icon="warehouse" />
            <Card label="Mặt hàng đang quản lý" value={fmt(s?.item_count)} note="Tổng mặt hàng trong ngày đang chọn" icon="box" />
            <Card label="Tồn hiện có" value={fmt(s?.on_hand_units)} note="Tổng tồn của các kho trong phương án" icon="grid" />
            <Card label="Kho cần bổ sung" value={summary.data?.warehouse_stock ? fmt(summary.data.warehouse_stock.filter((w) => Number(w.replenish_items) > 0).length) : "—"} note="Có ít nhất một mặt hàng cần đặt thêm" icon="truck" tone="orange" />
          </div> : <div className="stats">
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
          </div>}
          <State loading={summary.loading} error={summary.error} />
          {!insideWarehouse ? <WarehouseDirectory key={run.id} warehouses={warehouses} stock={summary.data?.warehouse_stock}
            loading={catalog?.loading} error={catalog?.error} onChoose={onWarehouse} /> :
          catalog?.data && !warehouse ? <div className="notice error" role="alert">Không tìm thấy kho trong phương án này. Hãy quay lại danh sách kho.</div> : <Panel
            title="Sản phẩm trong kho"
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
            <div className="inventory-filters">
              <label>Nhà mạng (carrier)
                <select aria-label="Nhà mạng trong kho" value={ctx.supplierId} onChange={(e) => onFilterChange?.({ supplierId: e.target.value, itemId: "" })}>
                  <option value="">Tất cả nhà mạng</option>
                  {supplierOptions.map((supplier) => <option key={String(supplier.id)} value={String(supplier.id)}>{String(supplier.carrier)}</option>)}
                </select>
              </label>
              <label>Loại sản phẩm
                <select aria-label="Loại sản phẩm trong kho" value={ctx.productType} onChange={(e) => onFilterChange?.({ productType: e.target.value, itemId: "" })}>
                  <option value="">Tất cả loại</option><option>eSIM</option><option>physical_SIM</option>
                </select>
              </label>
              <label>Mã sản phẩm
                <select aria-label="SKU trong kho" value={ctx.itemId} onChange={(e) => onFilterChange?.({ itemId: e.target.value })}>
                  <option value="">Tất cả sản phẩm</option>
                  {itemOptions.filter((i) => !ctx.productType || i.product_type === ctx.productType).map((i) => <option key={String(i.id)} value={String(i.id)}>{String(i.sku)} · {String(i.product_type)}</option>)}
                </select>
              </label>
              {(ctx.productType || ctx.supplierId || ctx.itemId || status) && <button className="text-button" onClick={() => { onFilterChange?.({ productType: "", supplierId: "", itemId: "" }); setStatus(""); }}>Xóa bộ lọc sản phẩm</button>}
            </div>
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
                    label: "Nhà mạng",
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
          </Panel>}
          {insideWarehouse && run.kind === "stock_projection" && (
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
