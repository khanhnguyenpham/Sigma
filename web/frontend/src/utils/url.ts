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
    warehouse_id: ctx.warehouseScope === "receiving" ? undefined : ctx.warehouseId,
    receiving_warehouse_id: ctx.warehouseScope === "receiving" ? ctx.warehouseId : undefined,
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
    ...(p.has("scenario_id") ? { scenarioId: p.get("scenario_id") ?? "" } : {}),
    warehouseId: p.get("warehouse_id") ?? "",
    ...(p.get("warehouse_scope") === "receiving" ? { warehouseScope: "receiving" as const } : {}),
    itemId: p.get("item_id") ?? "",
    productType: p.get("product_type") ?? "",
    supplierId: p.get("supplier_id") ?? "",
    origin: p.get("origin") ?? "",
    ...Object.fromEntries([["carrier","carrier"],["internal_status","internalStatus"],["provider_status","providerStatus"],["replenishment_allowed","replenishmentAllowed"],["sales_allowed","salesAllowed"],["window_origin","windowOrigin"]].filter(([key])=>p.has(key)).map(([key,value])=>[value,p.get(key)])),
  };
}

export function contextUrl(ctx: Context) {
  return query({
    run_id: ctx.runId,
    scenario_id: ctx.scenarioId,
    warehouse_id: ctx.warehouseId,
    warehouse_scope: ctx.warehouseScope,
    item_id: ctx.itemId,
    product_type: ctx.productType,
    supplier_id: ctx.supplierId,
    carrier: ctx.carrier,
    origin: ctx.origin,
    internal_status: ctx.internalStatus,
    provider_status: ctx.providerStatus,
    replenishment_allowed: ctx.replenishmentAllowed,
    sales_allowed: ctx.salesAllowed,
    window_origin: ctx.windowOrigin,
  });
}

export function navigationUrl(ctx:Context,page:string,view:PurchasingView) {
  if (page === "configuration") page = "scenarios";
  const params=new URLSearchParams(contextUrl(ctx));
  if(page.startsWith("provider-"))new URLSearchParams(location.search).forEach((v,k)=>{if(k.startsWith("notice_"))params.set(k,v);});
  if(page==="replenishment")params.set("view",view);
  return "?"+params.toString()+"#"+page;
}

export function readPage() {
  const page = location.hash.slice(1) || "overview";
  return page === "configuration" ? "scenarios" : page;
}

export function readPurchasingView(): PurchasingView {
  const view = new URLSearchParams(location.search).get("view");
  return view === "incoming" || view === "history" ? view : "recommendations";
}
