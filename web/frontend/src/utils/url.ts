import { type Context, type PurchasingView } from "../types/context";
import { OPS_TAB, TOOL_PAGES, isManagementPage } from "../config/navigation";

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
    ...extra,
  });
}

export function readContext(): Context {
  const p = new URLSearchParams(location.search);
  return {
    runId: p.get("run_id") ?? "",
    ...(p.has("ops_tab") ? { opsTab: p.get("ops_tab")! } : {}),
    ...(/^\d+$/.test(p.get("ops_order") ?? "") ? { opsOrderId: p.get("ops_order")! } : {}),
    ...(/^\d+$/.test(p.get("ops_supplier") ?? "") ? { opsSupplierId: p.get("ops_supplier")! } : {}),
    ...(/^\d+$/.test(p.get("ops_warehouse") ?? "") ? { opsWarehouseId: p.get("ops_warehouse")! } : {}),
    ...(p.has("scenario_id") ? { scenarioId: p.get("scenario_id") ?? "" } : {}),
    warehouseId: p.get("warehouse_id") ?? "",
    ...(p.get("warehouse_scope") === "receiving" ? { warehouseScope: "receiving" as const } : {}),
    itemId: p.get("item_id") ?? "",
    productType: p.get("product_type") ?? "",
    supplierId: p.get("supplier_id") ?? "",
    origin: p.get("origin") ?? "",
    ...(["low_stock", "pending_covers"].includes(p.get("inventory_state") ?? "") ? { inventoryState: p.get("inventory_state")! } : {}),
    ...Object.fromEntries([["warehouse_search", "warehouseSearch"], ["warehouse_country", "warehouseCountry"], ["warehouse_carrier", "warehouseCarrier"]]
      .filter(([key]) => p.has(key)).map(([key, field]) => [field, (p.get(key) ?? "").slice(0, 120)])),
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
    inventory_state: ctx.inventoryState,
    warehouse_search: ctx.warehouseSearch,
    warehouse_country: ctx.warehouseCountry,
    warehouse_carrier: ctx.warehouseCarrier,
    internal_status: ctx.internalStatus,
    provider_status: ctx.providerStatus,
    replenishment_allowed: ctx.replenishmentAllowed,
    sales_allowed: ctx.salesAllowed,
    window_origin: ctx.windowOrigin,
  });
}

export function navigationUrl(ctx:Context,page:string,view:PurchasingView) {
  if (isManagementPage(page)) return "?" + query({ ops_order: page === "orders" ? ctx.opsOrderId : undefined, ops_supplier: page === "suppliers" ? ctx.opsSupplierId : undefined, ops_warehouse: page === "stock" ? ctx.opsWarehouseId : undefined }) + "#" + page;
  if (page === "configuration") page = "scenarios";
  const params=new URLSearchParams(contextUrl(ctx));
  if(page.startsWith("provider-"))new URLSearchParams(location.search).forEach((v,k)=>{if(k.startsWith("notice_"))params.set(k,v);});
  if(page==="replenishment")params.set("view",view);
  return "?"+params.toString()+"#"+page;
}

export function readPage() {
  const params = new URLSearchParams(location.search);
  if (!location.hash) return params.has("run_id") ? "overview" : "dashboard";
  const page = location.hash.slice(1);
  // Legacy single-page links: ?ops_tab=orders#operations.
  if (page === "operations") return Object.keys(OPS_TAB).find((id) => OPS_TAB[id] === params.get("ops_tab")) ?? "stock";
  if (page === "product-supply") return new URLSearchParams(location.search).get("item_id") ? "product" : "products";
  if (page.startsWith("provider-")) return "scenarios";
  if (page === "configuration") return "scenarios";
  // Unknown hashes (old bookmarks, the dealer portal's own tabs) land on the dashboard instead of an empty tool page.
  return isManagementPage(page) || page === "product" || TOOL_PAGES.some(([id]) => id === page) ? page : "dashboard";
}

export function readPurchasingView(): PurchasingView {
  const view = new URLSearchParams(location.search).get("view");
  return view === "incoming" || view === "history" ? view : "recommendations";
}
