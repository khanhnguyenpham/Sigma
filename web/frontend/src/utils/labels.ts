import { ApiError } from "../services/http";

export function alertTypeLabel(value: unknown) {
  return ({ depletion: "Nguy cơ cạn", below_rop: "Dưới ngưỡng nhập", projected_below_rop: "Dự kiến xuống ROP" } as Record<string, string>)[String(value)] ?? String(value ?? "—");
}

export function label(kind: string) {
  return (
    (
      {
        source_import: "Nguồn dữ liệu",
        forecast: "Dự báo 46 tuyến",
        policy_replay: "Kế hoạch nhập hàng",
        alert_replay: "Kiểm tra cảnh báo",
        stock_projection: "Kế hoạch tồn kho",
        queued: "Đang xếp hàng",
        running: "Đang xử lý",
        complete: "Đã hoàn tất",
        failed: "Chưa hoàn tất",
        invalidated: "Không còn hợp lệ",
      } as Record<string, string>
    )[kind] ?? kind
  );
}

export function errorLabel(error: Error) {
  const code = error instanceof ApiError ? error.code : "";
  if (error instanceof ApiError && error.status === 429 && error.details?.retry_after_seconds)
    return `${error.message} Thử lại sau ${error.details.retry_after_seconds} giây.`;
  return (
    (
      {
        run_not_complete:
          "Lượt chạy chưa hoàn tất. Hãy theo dõi tiến độ tại Kịch bản.",
        scenario_deleted: "Kịch bản đang trong thùng rác. Khôi phục trước khi chạy hoặc lưu phiên bản mới.",
        scenario_busy: "Kịch bản còn run đang xếp hàng hoặc xử lý. Chờ hoàn tất trước khi xóa.",
        parent_mismatch:
          "Nguồn, phiên bản hoặc lượt dự báo chưa tương thích. Vui lòng chọn lại.",
        missing_partner_config:
          "Chưa đủ cấu hình nhập hàng có hiệu lực. Hãy kiểm tra thông tin sản phẩm.",
        supplier_carrier_mismatch:
          "Nhà cung cấp phải là nhà mạng (carrier) của mặt hàng.",
        missing_contract_quantity:
          "Hãy khai báo lượng nhập mỗi lần trong thông tin sản phẩm.",
        feature_not_in_run: "Kế hoạch này chưa có dự kiến bán theo tồn. Tạo kế hoạch mới để xem.",
        trade_schema_required: "Quản lý vòng đời mua bán chưa được bật cho dữ liệu này.",
        receiving_schema_required: "Kho nhận hàng chưa được bật cho dữ liệu này.",
        invalid_receiving_snapshot: "Kế hoạch thiếu thông tin kho nhận đã chốt. Chọn kế hoạch khác hoặc tạo mới.",
        trade_profile_required: "Cấu hình có hạn chế mua bán mới. Chọn tạo kế hoạch có hỗ trợ hai nguồn hạn chế.",
        preview_stale: "Phạm vi, cấu hình hoặc kế hoạch tác động đã thay đổi. Tải lại và xem lại tác động trước khi lưu.",
        provider_conflict: "Trạng thái thông báo đã thay đổi. Kiểm tra lịch sử trước khi thao tác lại.",
        invalid_trade_history: "Kế hoạch thiếu lịch sử mua bán phù hợp. Chọn kế hoạch khác hoặc tạo mới.",
        provider_scope_incomplete: "Danh mục đã thay đổi phạm vi. Kiểm tra và khai báo đủ sản phẩm/kho trước khi lập kế hoạch.",
        invalid_input: "Hãy kiểm tra các trường, ngày và phạm vi được chọn.",
        supply_schema_required: "Quản lý tình trạng cung cấp chưa được bật cho dữ liệu này.",
        supply_conflict: "Lịch cung cấp đã thay đổi hoặc ngày đang chọn không còn phù hợp. Tải lại và kiểm tra ngày trước khi lưu.",
        invalid_supply_history: "Chưa thể đọc lịch cung cấp của kế hoạch này. Hãy chọn kế hoạch khác hoặc tạo mới.",
        insufficient_forecast: "Thiếu đủ 14 ngày dự báo cho mặt hàng.",
        version_conflict: "Cấu hình đã thay đổi. Tải lại trước khi lưu.",
        database_unavailable:
          "Chưa kết nối được database. Kiểm tra dịch vụ local.",
        not_found: "Không tìm thấy dữ liệu hoặc lượt chạy đã chọn.",
      } as Record<string, string>
    )[code] ?? error.message
  );
}
