export interface Context {
  opsTab?: string;
  opsOrderId?: string;
  opsSupplierId?: string;
  opsWarehouseId?: string;
  runId: string;
  scenarioId?: string;
  warehouseId: string;
  warehouseScope?: "receiving";
  itemId: string;
  productType: string;
  supplierId: string;
  carrier?: string;
  origin: string;
  internalStatus?: string;
  providerStatus?: string;
  replenishmentAllowed?: string;
  salesAllowed?: string;
  windowOrigin?: string;
  inventoryState?: string;
  warehouseSearch?: string;
  warehouseCountry?: string;
  warehouseCarrier?: string;
}

export type PurchasingView = "recommendations" | "incoming" | "history";
