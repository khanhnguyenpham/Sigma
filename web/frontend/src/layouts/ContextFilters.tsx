import { inventoryKinds } from "../config/navigation";
import { label } from "../utils/labels";
import { text } from "../utils/format";
import { badge } from "../components/ui/Badge";
import { Icon } from "../components/ui/Icon";
import { warehouseName } from "../utils/warehouse";

import { type AppContextState } from "../hooks/useAppContext";
import { RunSnapshot } from "../components/configuration/RunSnapshot";

export function ContextFilters({ app, hideRunSelector = false }: { app: AppContextState; hideRunSelector?: boolean }) {
  const { ctx, setCtx, runs, selectRun, catalog, items, run, suppliers } = app;
  const inventoryPage = app.page === "inventory";
  const snapshotDate = run?.kind === "stock_projection" ? run.as_of_date : undefined;
  const warehouse = catalog.data?.items.find((w) => String(w.id) === ctx.warehouseId);
  return (
    <>
      <section className={"context-bar" + (inventoryPage ? " warehouse-context" : "")} aria-label="Bộ lọc cùng lượt chạy">
        {!hideRunSelector && <label className="plan-filter">
          Phương án
          <select
            aria-label="Lượt chạy"
            value={ctx.runId}
            onChange={(e) => selectRun(e.target.value)}
          >
            <option value="">Chọn phương án</option>
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                {label(r.kind)} · {r.as_of_date} · {r.id.slice(0, 6)}
                {r.status === "complete" ? "" : " · " + text(r.status)}
              </option>
            ))}
          </select>
        </label>}
        {!inventoryPage && <><label>
          {ctx.warehouseScope === "receiving" ? "Kho nhận hàng" : "Kho"}
          <select
            aria-label={ctx.warehouseScope === "receiving" ? "Kho nhận hàng" : "Kho / tuyến"}
            value={ctx.warehouseId}
            onChange={(e) =>
              setCtx((c) => ({
                ...c,
                warehouseId: e.target.value,
                itemId: "",
              }))
            }
          >
            <option value="">Tất cả kho</option>
            {catalog.data?.items.map((w) => (
              <option key={String(w.id)} value={String(w.id)}>
                {warehouseName(w)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Mặt hàng
          <select
            aria-label="SKU"
            disabled={!ctx.warehouseId}
            value={ctx.itemId}
            onChange={(e) => setCtx((c) => ({ ...c, itemId: e.target.value }))}
          >
            <option value="">
              {ctx.warehouseId ? "Tất cả mặt hàng" : "Chọn kho trước"}
            </option>
            {items.data?.items.map((i) => (
              <option key={String(i.id)} value={String(i.id)}>
                {String(i.sku)} · {String(i.product_type)}
              </option>
            ))}
          </select>
        </label>
        </>}
        <label>
          {snapshotDate ? "Ngày số liệu · UTC" : "Ngày kế hoạch · UTC"}
          <input
            aria-label={snapshotDate ? "Ngày số liệu UTC" : "Ngày xem / origin UTC"}
            aria-describedby={snapshotDate ? "snapshot-date-note" : undefined}
            type="date"
            value={snapshotDate ?? ctx.origin}
            readOnly={!!snapshotDate}
            onChange={(e) => setCtx((c) => ({ ...c, origin: e.target.value }))}
          />
        </label>
        {!inventoryPage && <details className="extra-filters">
          <summary>
            <Icon name="filter" size={16} /> Bộ lọc
          </summary>
          <div className="filter-popover">
            <label>
              Loại sản phẩm
              <select
                aria-label="Loại sản phẩm"
                value={ctx.productType}
                onChange={(e) =>
                  setCtx((c) => ({
                    ...c,
                    productType: e.target.value,
                    itemId: "",
                  }))
                }
              >
                <option value="">Tất cả</option>
                <option>eSIM</option>
                <option>physical_SIM</option>
              </select>
            </label>
            <label>
              Nhà mạng (carrier)
              <select
                aria-label="Nhà cung cấp"
                disabled={!run || !inventoryKinds.includes(run.kind)}
                value={ctx.supplierId}
                onChange={(e) =>
                  setCtx((c) => ({ ...c, supplierId: e.target.value }))
                }
              >
                <option value="">Tất cả</option>
                {suppliers.data?.items.map((s) => (
                  <option key={String(s.id)} value={String(s.id)}>
                    {String(s.carrier)}
                  </option>
                ))}
              </select>
            </label>
            <button
              className="text-button"
              onClick={() =>
                setCtx((c) => ({
                  ...c,
                  warehouseId: "",
                  itemId: "",
                  supplierId: "",
                  productType: "",
                  inventoryState: "",
                  warehouseSearch: "", warehouseCountry: "", warehouseCarrier: "",
                }))
              }
            >
              Xóa bộ lọc
            </button>
          </div>
        </details>}
      </section>
      {snapshotDate && <div className="context-date-note" id="snapshot-date-note">
        <span>Phương án này chỉ có số liệu tồn kho tại ngày {snapshotDate.split("-").reverse().join("/")}. Có thể chọn ngày đánh giá riêng trong phần So sánh dự báo / thực tế.</span>
        {app.page !== "forecast" && <button type="button" className="text-button" onClick={() => app.navigate("forecast")}>Xem so sánh 14 ngày <Icon name="arrow" size={15} /></button>}
      </div>}
      {!inventoryPage && warehouse && <div className="warehouse-scope" aria-label="Kho đang chọn">
        <Icon name="warehouse" size={17} /><span>Kho <strong>{warehouseName(warehouse)}</strong></span>
        <span>{String(warehouse.destination_country)}</span>{ctx.warehouseScope !== "receiving" && <span>Nhà mạng <strong>{String(warehouse.carrier)}</strong></span>}
      </div>}
      <div className="context-meta">
        {run && (
          <>
            <span>
              {badge(run.status)}
              <span className="plan-type">{label(run.kind)}</span>
            </span>
            <RunSnapshot key={run.id} run={run} title="Xem cấu hình snapshot" />
          </>
        )}
      </div>
    </>
  );
}
