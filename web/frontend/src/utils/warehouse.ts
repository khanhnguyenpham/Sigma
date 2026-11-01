import type { Row } from "../types/api";

export function warehouseName(warehouse?: Row) {
  if (typeof warehouse?.display_city === "string" && warehouse.display_city.trim()) return warehouse.display_city;
  return typeof warehouse?.city === "string" && warehouse.city.trim()
    ? warehouse.city
    : "Chưa đặt tên";
}
