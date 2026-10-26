import { text } from "../../utils/format";

export const badge = (value: unknown) => (
  <span className={"badge " + String(value)}>
    {(
      {
        early: "Sớm ≥7 ngày",
        urgent: "Khẩn · dưới 7 ngày",
        already_depleted: "Đã hết tại mốc chốt",
        not_within_horizon: "Chưa cạn trong 14 ngày",
        pending_covers: "Dưới ROP · đã đặt đủ",
        low_stock: "Cần bổ sung",
        threshold_warning: "Dự kiến xuống ROP",
        sufficient: "Đủ tồn",
        complete: "Hoàn tất",
        running: "Đang chạy",
        queued: "Đang chờ",
        failed: "Lỗi",
        received: "Đã nhận",
        ordered: "Đang về",
      } as Record<string, string>
    )[String(value)] ?? text(value)}
  </span>
);
