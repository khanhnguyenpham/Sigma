export interface Context {
  runId: string;
  warehouseId: string;
  itemId: string;
  productType: string;
  supplierId: string;
  origin: string;
}

export type PurchasingView = "recommendations" | "incoming" | "history";
