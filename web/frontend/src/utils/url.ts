import { type Context, type PurchasingView } from "../types/context";

export function query(
  values: Record<string, string | number | undefined | null>,
) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([k, v]) => {
    if (v !== "" && v !== undefined && v !== null) params.set(k, String(v));
  });
  return params.toString();
}

export function resultQuery(
  ctx: Context,
  extra: Record<string, string | number | undefined | null> = {},
) {
  return query({
    warehouse_id: ctx.warehouseId,
    item_id: ctx.itemId,
    product_type: ctx.productType,
    supplier_id: ctx.supplierId,
    ...extra,
  });
}

export function readContext(): Context {
  const p = new URLSearchParams(location.search);
  return {
    runId: p.get("run_id") ?? "",
    warehouseId: p.get("warehouse_id") ?? "",
    itemId: p.get("item_id") ?? "",
    productType: p.get("product_type") ?? "",
    supplierId: p.get("supplier_id") ?? "",
    origin: p.get("origin") ?? "",
  };
}

export function contextUrl(ctx: Context) {
  return query({
    run_id: ctx.runId,
    warehouse_id: ctx.warehouseId,
    item_id: ctx.itemId,
    product_type: ctx.productType,
    supplier_id: ctx.supplierId,
    origin: ctx.origin,
  });
}

export function readPurchasingView(): PurchasingView {
  const view = new URLSearchParams(location.search).get("view");
  return view === "incoming" || view === "history" ? view : "recommendations";
}
