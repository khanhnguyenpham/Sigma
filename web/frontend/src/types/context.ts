export interface Context {
  runId: string;
  warehouseId: string;
  itemId: string;
  productType: string;
  supplierId: string;
  origin: string;
  internalStatus?: string;
  providerStatus?: string;
  replenishmentAllowed?: string;
  salesAllowed?: string;
  windowOrigin?: string;
}

export type PurchasingView = "recommendations" | "incoming" | "history";
