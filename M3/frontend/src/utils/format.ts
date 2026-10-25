export const text = (value: unknown) =>
  value === null || value === undefined ? "—" : String(value);

export const num = (value: unknown) =>
  typeof value === "number" && Number.isFinite(value) ? value : null;

export const fmt = (value: unknown, digits = 0) =>
  num(value) === null
    ? "—"
    : new Intl.NumberFormat("vi-VN", {
        maximumFractionDigits: digits,
        minimumFractionDigits: digits,
      }).format(value as number);

export const pct = (value: unknown) =>
  num(value) === null ? "—" : fmt((value as number) * 100, 1) + "%";
