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
        missing_contract_quantity:
          "Hãy cấu hình lượng nhập mỗi lần cho mặt hàng. Kịch bản không được đổi lượng này.",
        insufficient_forecast: "Thiếu đủ 14 ngày dự báo cho mặt hàng.",
        version_conflict: "Cấu hình đã thay đổi. Tải lại trước khi lưu.",
        database_unavailable:
          "Chưa kết nối được database. Kiểm tra dịch vụ local.",
        not_found: "Không tìm thấy dữ liệu hoặc lượt chạy đã chọn.",
      } as Record<string, string>
    )[code] ?? error.message
  );
}
