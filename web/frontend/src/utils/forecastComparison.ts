import type { Row } from "../types/api";

export function forecastDay(day: string, offset: number) {
  const value = new Date(day + "T00:00:00Z");
  value.setUTCDate(value.getUTCDate() + offset);
  return value.toISOString().slice(0, 10);
}

export function compareForecast14(rows: Row[], origin: string, daily: boolean) {
  const expected = new Set(daily ? Array.from({ length: 14 }, (_, i) => forecastDay(origin, i + 1)) : ["1", "2"]);
  const grouped = new Map<string, Row[]>();
  for (const row of rows) {
    const key = String(row.warehouse_id);
    grouped.set(key, [...(grouped.get(key) ?? []), row]);
  }
  const valid = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value) && value >= 0;
  const items = Array.from(grouped, ([key, parts]) => {
    const periods = parts.map(row => String(daily ? row.target_date : row.block));
    const complete = parts.length === expected.size && new Set(periods).size === expected.size && periods.every(value => expected.has(value));
    const forecast = complete && parts.every(row => valid(row.forecast_qty))
      ? parts.reduce((sum, row) => sum + Number(row.forecast_qty), 0) : null;
    const actual = complete && parts.every(row => row.actual_available === true && valid(row.actual_qty))
      ? parts.reduce((sum, row) => sum + Number(row.actual_qty), 0) : null;
    return { id: key, warehouse_id: parts[0].warehouse_id, destination_country: parts[0].destination_country,
      carrier: parts[0].carrier, forecast_qty: forecast, actual_qty: actual,
      difference_qty: forecast !== null && actual !== null ? forecast - actual : null };
  });
  const forecast = items.length && items.every(row => row.forecast_qty !== null)
    ? items.reduce((sum, row) => sum + row.forecast_qty!, 0) : null;
  const actual = items.length && items.every(row => row.actual_qty !== null)
    ? items.reduce((sum, row) => sum + row.actual_qty!, 0) : null;
  return { items, forecast, actual, difference: forecast !== null && actual !== null ? forecast - actual : null,
    actualRoutes: items.filter(row => row.actual_qty !== null).length };
}
