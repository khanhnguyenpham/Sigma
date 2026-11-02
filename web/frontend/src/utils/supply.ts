import type { Row } from "../types/api";

export function addSupplyDays(day: string, days = 7) {
  const date = new Date(day + "T00:00:00Z");
  if (!day || Number.isNaN(date.getTime())) return "";
  date.setUTCDate(date.getUTCDate() + days);
  return date.getUTCFullYear() > 9999 ? "" : date.toISOString().slice(0, 10);
}

export function inventoryStatus(row: Row) {
  if (row.replenishment_allowed === false) return String(row.sell_through_state ?? "stopped");
  return row.needs_replenishment ? Number(row.recommended_qty) > 0 ? "low_stock" : "pending_covers" : "sufficient";
}
