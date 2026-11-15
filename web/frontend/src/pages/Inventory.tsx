import { inventoryStatus } from "../utils/supply";
import { WarehouseEditor } from "../components/inventory/WarehouseEditor";
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
import { InventoryActions } from "../components/inventory/InventoryActions";
import { InventoryFilters } from "../components/inventory/InventoryFilters";
import { Card } from "../components/ui/Card";

import { PlanRequired } from "../components/ui/PlanRequired";
import { badge } from "../components/ui/Badge";
import type { PurchasingView } from "../types/context";
import { Icon } from "../components/ui/Icon";
import type { WorkspaceData } from "../types/api";
import { WarehouseDirectory } from "../components/inventory/WarehouseDirectory";
import { warehouseName, isReceivingRun } from "../utils/warehouse";
import { TradeTotals } from "../components/products/TradePresentation";
import { isTradeRun } from "../utils/trade";
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
    [localStatus, setLocalStatus] = useState(ctx.inventoryState ?? ""),
    [editingWarehouse, setEditingWarehouse] = useState(false);
  const receiving = isReceivingRun(run);
  const status = onFilterChange ? ctx.inventoryState ?? "" : localStatus;
  function setStatus(value: string) {
    setLocalStatus(value);
    onFilterChange?.({ inventoryState: value });
  }
  const key = JSON.stringify([ctx, status]);
  useEffect(() => setPage(1), [key]);
  useEffect(() => setLocalStatus(ctx.inventoryState ?? ""), [ctx.runId, ctx.warehouseId, ctx.inventoryState]);
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
    <div className="inventory-page">
      {insideWarehouse && <nav className="warehouse-breadcrumb" aria-label="Đường dẫn kho">
        <button className="text-button" onClick={() => onWarehouse?.("")}><span aria-hidden="true">←</span> Danh sách kho</button>
        <span aria-hidden="true">/</span><span aria-current="page">{warehouseName(warehouse)}</span>
      </nav>}
      <div className="page-heading">
        <div>
          <h1>{insideWarehouse ? warehouseName(warehouse) : "Tồn kho"}</h1>
          <p>
            {insideWarehouse ? `${text(warehouse?.destination_country)}${warehouse && !receiving ? ` · ${String(warehouse.carrier)}` : ""}` : "Bắt đầu từ kho đang quản lý, sau đó chọn kho để xem sản phẩm bên trong."}
          </p>
        </div>
        {insideWarehouse && <InventoryActions onEdit={() => setEditingWarehouse(true)}
          onForecast={ready && onNavigate ? () => onNavigate("forecast") : undefined}
          onReplenishment={ready && onNavigate ? () => onNavigate("replenishment") : undefined}
          exportUrl={ready ? `/runs/${run!.id}/exports/inventory_daily?${q}` : undefined} />}
      </div>
      {!ready && insideWarehouse ? (
        <PlanRequired onChoose={onChoose} />
      ) : (
        <>
          {!insideWarehouse ? <div className="stats">
            <Card label="Kho đang quản lý" value={catalog?.data ? fmt(warehouses.length) : "—"} note="Mỗi kho có một địa danh riêng" icon="warehouse" />
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
          <TradeTotals summary={s} />
          {!insideWarehouse ? <WarehouseDirectory key={run?.id} warehouses={warehouses} stock={summary.data?.warehouse_stock}
            filters={onFilterChange ? { search: ctx.warehouseSearch ?? "", country: ctx.warehouseCountry ?? "", carrier: ctx.warehouseCarrier ?? "" } : undefined}
            onFiltersChange={onFilterChange ? (value) => onFilterChange({ warehouseSearch: value.search, warehouseCountry: value.country, warehouseCarrier: value.carrier }) : undefined}
            loading={catalog?.loading} error={catalog?.error} onChoose={onWarehouse} receiving={receiving} /> :
          catalog?.data && !warehouse ? <div className="notice error" role="alert">Không tìm thấy kho trong phương án này. Hãy quay lại danh sách kho.</div> : <Panel
            title="Sản phẩm trong kho"
            note="Chọn một sản phẩm để xem chi tiết."
          >
            {status && <p className="filter-scope-note">Lọc trạng thái chỉ áp dụng cho bảng; các thẻ là tổng trong phạm vi kho và sản phẩm.</p>}
            <InventoryFilters ctx={ctx} status={status} onStatus={setStatus} onChange={onFilterChange}
              itemOptions={itemOptions} supplierOptions={supplierOptions} />
            <State
              error={data.error}
            />
            {!data.error && (
              <Table
                stickyFirstColumn
                rows={rows}
                loading={data.loading}
                emptyMessage={status || ctx.itemId || ctx.productType || ctx.supplierId ? "Không có kết quả phù hợp với bộ lọc." : "Không có dữ liệu tồn kho tại ngày đang xem."}
                onRow={(row) => onItem?.(row, "product")}
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
                  ...(isTradeRun(run)?[{key:"sellable_qty",label:"Tồn được bán"},{key:"blocked_qty",label:"Tồn bị chặn"}]:[]),
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
                      badge(inventoryStatus(r)),
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
          {insideWarehouse && run?.kind === "stock_projection" && (
            <p className="caption">
              Số tồn tại mốc chốt được khởi tạo theo phương án mô phỏng. Các
              ngày sau mốc chốt là dự kiến; chưa ghi nhận là tồn thực tế.
            </p>
          )}
        </>
      )}
      {editingWarehouse && <WarehouseEditor key={ctx.warehouseId} id={ctx.warehouseId} onClose={() => setEditingWarehouse(false)} />}
    </div>
  );
}
