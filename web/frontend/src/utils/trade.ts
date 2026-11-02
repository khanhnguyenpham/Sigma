import type { Row, Run } from "../types/api";
export const TRADE_PROFILE = "internal_provider_trade_v2";
export const isTradeRun = (run?: Run) => run?.trade_lifecycle_profile === TRADE_PROFILE || run?.result_summary.trade_lifecycle_profile === TRADE_PROFILE;
export const isTradeRow = (row: Row) => row.trade_lifecycle_profile === TRADE_PROFILE || typeof row.sales_allowed === "boolean";
export const internalLabel = (value: unknown) => ({active:"Đang cho nhập",scheduled_stop:"Đã lên lịch ngừng nhập",stopped:"Đã ngừng nhập nội bộ"}[String(value)] ?? "Chưa có trạng thái theo ngày");
export const providerLabel = (value: unknown) => ({clear:"Không bị chặn bán",scheduled_stop:"Nhà mạng sắp ngừng sản phẩm",stopped:"Nhà mạng ngừng mua và bán",scheduled_resume:"Chờ cung cấp trở lại"}[String(value)] ?? "Chưa có trạng thái theo ngày");
export const capLabel = (value: unknown) => value==null?"Không áp giới hạn":({internal_stopped:"Đã ngừng nhập nội bộ",provider_blocked:"Nhà mạng chặn mua và bán",eta_at_or_after_provider_stop:"Hàng về từ ngày nhà mạng ngừng sản phẩm",insufficient_forecast_coverage:"Chưa đủ dự báo tới ngày ngừng",fixed_lot_exceeds_sellable_budget:"Lượng mỗi lần vượt khả năng bán trước hạn"}[String(value)] ?? "Chưa có dữ liệu giới hạn");
export const canRecommend = (row: Row) => row.replenishment_allowed !== false && (isTradeRow(row) ? row.actionable === true && Number(row.q_final ?? row.recommended_qty) > 0 : Number(row.recommended_qty ?? 1) > 0);
