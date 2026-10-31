import type { Row } from "../types/api";

export function warehouseName(warehouse?: Row) {
  return typeof warehouse?.city === "string" && warehouse.city.trim()
    ? warehouse.city
    : "Chưa đặt tên";
}
