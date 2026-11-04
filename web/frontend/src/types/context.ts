export interface Context {
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
}

export type PurchasingView = "recommendations" | "incoming" | "history";
