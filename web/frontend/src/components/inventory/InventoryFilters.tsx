import { useEffect, useState } from "react";
import type { Row } from "../../types/api";
import type { Context } from "../../types/context";
import { useMediaQuery } from "../../hooks/useMediaQuery";
import { Dialog } from "../ui/Dialog";
import { Icon } from "../ui/Icon";

type ProductFilters = Pick<Context, "supplierId" | "productType" | "itemId">;

export function InventoryFilters({ ctx, status, onStatus, onChange, itemOptions, supplierOptions }: {
  ctx: Context; status: string; onStatus: (value: string) => void;
  onChange?: (patch: Partial<Context>) => void; itemOptions: Row[]; supplierOptions: Row[];
}) {
  const compact = useMediaQuery("(max-width: 760px)");
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<ProductFilters>({ supplierId: "", productType: "", itemId: "" });
  useEffect(() => setOpen(false), [ctx.runId, ctx.warehouseId, compact]);
  const count = [ctx.supplierId, ctx.productType, ctx.itemId].filter(Boolean).length;
  function fields(values: ProductFilters, change: (patch: Partial<ProductFilters>) => void) {
    return <>
      <label>Nhà mạng<select aria-label="Nhà mạng trong kho" value={values.supplierId} onChange={(event) => change({ supplierId: event.target.value, itemId: "" })}>
        <option value="">Tất cả nhà mạng</option>{supplierOptions.map((supplier) => <option key={String(supplier.id)} value={String(supplier.id)}>{String(supplier.carrier)}</option>)}
      </select></label>
      <label>Loại sản phẩm<select aria-label="Loại sản phẩm trong kho" value={values.productType} onChange={(event) => change({ productType: event.target.value, itemId: "" })}>
        <option value="">Tất cả loại</option><option>eSIM</option><option>physical_SIM</option>
      </select></label>
      <label>Mã sản phẩm<select aria-label="SKU trong kho" value={values.itemId} onChange={(event) => change({ itemId: event.target.value })}>
        <option value="">Tất cả sản phẩm</option>{itemOptions.filter((item) => !values.productType || item.product_type === values.productType).map((item) =>
          <option key={String(item.id)} value={String(item.id)}>{String(item.sku)} · {String(item.product_type)}</option>)}
      </select></label>
    </>;
  }
  return <div className={`inventory-filters${compact ? " compact-inventory-filters" : ""}`}>
    <label>Trạng thái bổ sung<select aria-label="Trạng thái tồn kho" value={status} onChange={(event) => onStatus(event.target.value)}>
      <option value="">Tất cả trạng thái</option><option value="low_stock">Cần đặt thêm</option><option value="pending_covers">Đã có đủ hàng đang về</option>
    </select></label>
    {compact ? <button type="button" className="inventory-more-filters" aria-haspopup="dialog" onClick={() => {
      setDraft({ supplierId: ctx.supplierId, productType: ctx.productType, itemId: ctx.itemId }); setOpen(true);
    }}><Icon name="filter" size={16} />Lọc khác{count > 0 && <span className="filter-count">{count}</span>}</button>
      : fields(ctx, (patch) => onChange?.(patch))}
    {(count > 0 || status) && <button type="button" className="text-button" onClick={() => {
      onChange?.({ productType: "", supplierId: "", itemId: "" }); onStatus("");
    }}>Xóa bộ lọc sản phẩm</button>}
    {open && <Dialog title="Lọc sản phẩm trong kho" onClose={() => setOpen(false)} className="inventory-filter-dialog">
      <form onSubmit={(event) => { event.preventDefault(); onChange?.(draft); setOpen(false); }}>
        <div className="inventory-filter-fields">{fields(draft, (patch) => setDraft((previous) => ({ ...previous, ...patch })))}</div>
        <div className="dialog-form-actions"><button type="button" onClick={() => setDraft({ supplierId: "", productType: "", itemId: "" })}>Đặt lại</button>
          <button type="submit" className="primary">Áp dụng</button></div>
      </form>
    </Dialog>}
  </div>;
}
