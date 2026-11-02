import { inventoryKinds } from "../config/navigation";
import { label } from "../utils/labels";
import { text } from "../utils/format";
import { badge } from "../components/ui/Badge";
import { Icon } from "../components/ui/Icon";
import { warehouseName } from "../utils/warehouse";

import { type AppContextState } from "../hooks/useAppContext";
import { isTradeRun } from "../utils/trade";

export function ContextFilters({ app }: { app: AppContextState }) {
  const { ctx, setCtx, runs, selectRun, catalog, items, run, suppliers } = app;
  const inventoryPage = app.page === "inventory";
  const trade=isTradeRun(run),tradeFilter=!!(ctx.internalStatus || ctx.providerStatus || ctx.replenishmentAllowed || ctx.salesAllowed || ctx.windowOrigin);
  const warehouse = catalog.data?.items.find((w) => String(w.id) === ctx.warehouseId);
  return (
    <>
      <section className={"context-bar" + (inventoryPage ? " warehouse-context" : "")} aria-label="Bộ lọc cùng lượt chạy">
        <label className="plan-filter">
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
        </label>
        {!inventoryPage && <><label>
          Kho
          <select
            aria-label="Kho / tuyến"
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
          Ngày kế hoạch · UTC
          <input
            aria-label="Ngày xem / origin UTC"
            type="date"
            value={ctx.origin}
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
                }))
              }
            >
              Xóa bộ lọc
            </button>
          </div>
        </details>}
      </section>
      {(trade || tradeFilter) && <details className="advanced-section trade-result-filters"><summary>Lọc hạn chế trong kế hoạch đã chốt</summary>
        {!trade && <p className="notice">Quyền bán và tồn bị chặn không có trong kế hoạch này. Xóa bộ lọc mới hoặc chọn kế hoạch phù hợp.</p>}
        <fieldset disabled={!trade}><div className="provider-filters">
          <label>Nhập nội bộ trong kế hoạch<select value={ctx.internalStatus ?? ""} onChange={e=>setCtx(c=>({...c,internalStatus:e.target.value}))}><option value="">Tất cả</option><option value="active">Đang cho nhập</option><option value="scheduled_stop">Sắp ngừng nhập</option><option value="stopped">Đã ngừng nhập</option></select></label>
          <label>Nhà mạng trong kế hoạch<select value={ctx.providerStatus ?? ""} onChange={e=>setCtx(c=>({...c,providerStatus:e.target.value}))}><option value="">Tất cả</option><option value="clear">Không bị chặn</option><option value="scheduled_stop">Sắp ngừng sản phẩm</option><option value="stopped">Đã ngừng mua và bán</option><option value="scheduled_resume">Chờ cung cấp lại</option></select></label>
          <label>Quyền nhập trong kế hoạch<select value={ctx.replenishmentAllowed ?? ""} onChange={e=>setCtx(c=>({...c,replenishmentAllowed:e.target.value}))}><option value="">Tất cả</option><option value="true">Được nhập</option><option value="false">Không được nhập</option></select></label>
          <label>Quyền bán trong kế hoạch<select value={ctx.salesAllowed ?? ""} onChange={e=>setCtx(c=>({...c,salesAllowed:e.target.value}))}><option value="">Tất cả</option><option value="true">Được bán</option><option value="false">Không được bán</option></select></label>
          <label>Origin của cửa sổ UTC<input type="date" value={ctx.windowOrigin ?? ""} onChange={e=>setCtx(c=>({...c,windowOrigin:e.target.value}))} /></label>
        </div></fieldset><button className="text-button" onClick={()=>setCtx(c=>({...c,internalStatus:"",providerStatus:"",replenishmentAllowed:"",salesAllowed:"",windowOrigin:""}))}>Xóa bộ lọc hạn chế</button>
      </details>}
      {!inventoryPage && warehouse && <div className="warehouse-scope" aria-label="Kho đang chọn">
        <Icon name="warehouse" size={17} /><span>Kho <strong>{warehouseName(warehouse)}</strong></span>
        <span>{String(warehouse.destination_country)}</span><span>Nhà mạng <strong>{String(warehouse.carrier)}</strong></span>
      </div>}
      <div className="context-meta">
        {run && (
          <>
            <span>
              {badge(run.status)}
              <span className="plan-type">{label(run.kind)}</span>
            </span>
            <details>
              <summary>
                Thông tin phương án <Icon name="info" size={13} />
              </summary>
              <div className="context-popover">
                <strong>Nguồn & phiên bản</strong>
                <dl>
                  <dt>Mã phương án</dt>
                  <dd>{run.id}</dd>
                  <dt>Mốc chốt UTC</dt>
                  <dd>{run.as_of_date}</dd>
                  <dt>Quan sát đến</dt>
                  <dd>{run.observation_end}</dd>
                  <dt>Cấu hình</dt>
                  <dd>{run.config_version}</dd>
                  <dt>Giả định</dt>
                  <dd>{run.assumption_version}</dd>
                </dl>
                <p>
                  Snapshot lịch sử 2024–2025. Tồn và nhập là mô phỏng; chưa quan
                  sát actual sau 31/12/2025. L7 · R1 · H14.
                </p>
              </div>
            </details>
          </>
        )}
      </div>
    </>
  );
}
