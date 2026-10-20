import { CLOUD, cloudRequest } from "./cloud";
export type Row = Record<string, unknown>;
export interface Run {
  id: string;
  kind: string;
  status: string;
  as_of_date: string;
  observation_end: string;
  source_import_run_id: string | null;
  forecast_run_id: string | null;
  scenario_id: number | null;
  config_version: string;
  assumption_version: string;
  target_version: string;
  error_code: string | null;
  result_summary: Row;
  period_start: string | null;
  period_end: string | null;
  created_at: string;
}
export interface Context {
  runId: string;
  warehouseId: string;
  itemId: string;
  productType: string;
  supplierId: string;
  origin: string;
}
export interface Page<T = Row> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  context?: Row;
}
export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  if (CLOUD) {
    const reply = await cloudRequest(path, options);
    if (!reply.ok)
      throw new ApiError(
        reply.error?.code ?? "invalid_input",
        reply.error?.message ?? "Không thể thực hiện thao tác",
        reply.status,
      );
    return reply.data as T;
  }
  const response = await fetch("/api/v1" + path, options);
  const data = await response.json();
  if (!response.ok)
    throw new ApiError(
      data.error?.code ?? "network_error",
      data.error?.message ?? "Không thể tải dữ liệu",
      response.status,
    );
  return data;
}
export function query(
  values: Record<string, string | number | undefined | null>,
) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([k, v]) => {
    if (v !== "" && v !== undefined && v !== null) params.set(k, String(v));
  });
  return params.toString();
}
export function resultQuery(
  ctx: Context,
  extra: Record<string, string | number | undefined | null> = {},
) {
  return query({
    warehouse_id: ctx.warehouseId,
    item_id: ctx.itemId,
    product_type: ctx.productType,
    supplier_id: ctx.supplierId,
    ...extra,
  });
}
export function readContext(): Context {
  const p = new URLSearchParams(location.search);
  return {
    runId: p.get("run_id") ?? "",
    warehouseId: p.get("warehouse_id") ?? "",
    itemId: p.get("item_id") ?? "",
    productType: p.get("product_type") ?? "",
    supplierId: p.get("supplier_id") ?? "",
    origin: p.get("origin") ?? "",
  };
}
export function contextUrl(ctx: Context) {
  return query({
    run_id: ctx.runId,
    warehouse_id: ctx.warehouseId,
    item_id: ctx.itemId,
    product_type: ctx.productType,
    supplier_id: ctx.supplierId,
    origin: ctx.origin,
  });
}
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
export function label(kind: string) {
  return (
    (
      {
        source_import: "Nguồn dữ liệu",
        forecast: "Dự báo 46 tuyến",
        policy_replay: "Kế hoạch nhập hàng",
        alert_replay: "Kiểm tra cảnh báo",
        stock_projection: "Kế hoạch tồn kho",
      } as Record<string, string>
    )[kind] ?? kind
  );
}
export function errorLabel(error: Error) {
  const code = error instanceof ApiError ? error.code : "";
  return (
    (
      {
        monthly_not_prepared:
          "Nguồn này chưa có gói tổng 30 đã kiểm chứng. Xem hướng dẫn prepare-monthly trong M3.",
        monthly_invalid:
          "Gói tổng 30 không khớp nguồn hoặc checksum. Cần kiểm tra lại trước khi hiển thị.",
        run_not_complete:
          "Lượt chạy chưa hoàn tất. Hãy theo dõi tiến độ ở Tổng quan.",
        parent_mismatch:
          "Nguồn, phiên bản hoặc lượt dự báo chưa tương thích. Vui lòng chọn lại.",
        missing_partner_config:
          "Thiếu policy hiệu lực hoặc cấu hình nhập. Kiểm tra Cấu hình.",
        insufficient_forecast: "Thiếu đủ 14 ngày dự báo cho mặt hàng.",
        version_conflict: "Cấu hình đã thay đổi. Tải lại trước khi lưu.",
        database_unavailable:
          "Chưa kết nối được database. Kiểm tra dịch vụ local.",
        not_found: "Không tìm thấy dữ liệu hoặc lượt chạy đã chọn.",
      } as Record<string, string>
    )[code] ?? error.message
  );
}
