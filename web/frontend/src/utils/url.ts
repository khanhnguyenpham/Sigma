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
    internal_status: ctx.internalStatus,
    provider_status: ctx.providerStatus,
    replenishment_allowed: ctx.replenishmentAllowed,
    sales_allowed: ctx.salesAllowed,
    window_origin: ctx.windowOrigin,
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
    ...Object.fromEntries([["internal_status","internalStatus"],["provider_status","providerStatus"],["replenishment_allowed","replenishmentAllowed"],["sales_allowed","salesAllowed"],["window_origin","windowOrigin"]].filter(([key])=>p.has(key)).map(([key,value])=>[value,p.get(key)])),
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
    internal_status: ctx.internalStatus,
    provider_status: ctx.providerStatus,
    replenishment_allowed: ctx.replenishmentAllowed,
    sales_allowed: ctx.salesAllowed,
    window_origin: ctx.windowOrigin,
  });
}

export function navigationUrl(ctx:Context,page:string,view:PurchasingView) {
  const params=new URLSearchParams(contextUrl(ctx));
  if(page.startsWith("provider-"))new URLSearchParams(location.search).forEach((v,k)=>{if(k.startsWith("notice_"))params.set(k,v);});
  if(page==="replenishment")params.set("view",view);
  return "?"+params.toString()+"#"+page;
}

export function readPurchasingView(): PurchasingView {
  const view = new URLSearchParams(location.search).get("view");
  return view === "incoming" || view === "history" ? view : "recommendations";
}
