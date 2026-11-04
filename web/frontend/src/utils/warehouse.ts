import type { Row } from "../types/api";
import type { Run } from "../types/api";

export const isReceivingRun = (run?: Run) => run?.receiving_warehouse_profile === "product_default_receiving_v1"
  || run?.result_summary.receiving_warehouse_profile === "product_default_receiving_v1";

export function warehouseName(warehouse?: Row) {
  if (typeof warehouse?.receiving_display_city === "string" && warehouse.receiving_display_city.trim()) return warehouse.receiving_display_city;
  if (typeof warehouse?.receiving_city === "string" && warehouse.receiving_city.trim()) return warehouse.receiving_city;
  if (typeof warehouse?.display_city === "string" && warehouse.display_city.trim()) return warehouse.display_city;
  return typeof warehouse?.city === "string" && warehouse.city.trim()
    ? warehouse.city
    : "Chưa đặt tên";
}
