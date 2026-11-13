import report from "../../data/c00-forecast-floor-evaluation.json";
import reportUrl from "../../data/c00-forecast-floor-evaluation.json?url&no-inline";
import historical from "../../data/c00-evaluation.json";
import { fmt } from "../../utils/format";
import { Card } from "../ui/Card";
import { Panel } from "../ui/Panel";

const percent = (value: number | null) => value === null ? "Chưa xác định" : `${fmt(value * 100, 2)}%`;

export function C00Evaluation() {
  return <Panel title="Đánh giá C00 — hồi cứu toàn kỳ"
    note="Kết quả đã chạy lại và kiểm chứng độc lập trên bộ đầu vào, dự báo và chính sách đã chốt."
    action={<a className="button secondary" href={reportUrl} download="C00-hoi-cuu-2025.json">Tải kết quả C00</a>}>
    <p>Kỳ đánh giá: <strong>{report.score_start.split("-").reverse().join("/")} – {report.score_end.split("-").reverse().join("/")}</strong> · {fmt(report.policy_count)} mặt hàng · Cảnh báo trước ít nhất {report.minimum_lead_days} ngày.</p>
    <p><strong>ROP = max(nhu cầu dự báo 7 ngày + SS, ngưỡng nhập tối thiểu).</strong></p>
    <div className="stats">
      <Card label="C00 · Báo sớm ≥7 ngày" value={percent(report.eligible_early_rate)}
        note={`${report.early_numerator}/${report.eligible_event_count} đợt cạn có đủ thời gian báo sớm`} />
      <Card label="Precision cảnh báo" value={percent(report.precision)} note={`${fmt(report.alarm_tp)} đúng / ${fmt(report.alarm_fp)} sai, theo mặt hàng-ngày`} />
      <Card label="Recall theo đợt cạn" value={percent(report.recall)} note={`${report.matched_events}/${report.event_denominator} đợt cạn có cảnh báo`} />
      <Card label="Sai lệch ngày cạn trung bình" value={`${fmt(report.date_mae, 2)} ngày`} note={`Trên ${report.matched_events} đợt cạn có cảnh báo`} />
    </div>
    <p className="notice">Đây là kết quả nghiên cứu hồi cứu C00 với tự bổ sung hàng và {report.warmup_days} ngày khởi tạo. Kết quả cố định theo bộ dữ liệu đã chốt, không thay theo kịch bản hoặc bộ lọc đang chọn. Tỷ lệ của từng lượt Kiểm tra cảnh báo 14 ngày nằm trong tab Tóm tắt của kết quả lượt chạy.</p>
    <details className="advanced-section c00-evaluation-details">
      <summary>Cách tính và nguồn kết quả C00</summary>
      <p>Tỷ lệ mặc định là {report.early_numerator}/{report.eligible_event_count} ({percent(report.eligible_early_rate)}). Mẫu số gồm các đợt có ít nhất một ngày còn tồn dương trước khi cạn từ 7 đến 14 ngày mà cảnh báo có thể ghép với chính đợt đó. Các đợt đủ điều kiện nhưng bị bỏ sót vẫn được tính.</p>
      <p>Có {report.event_denominator - report.eligible_event_count} đợt thiếu cơ hội báo sớm. Nếu tính trên toàn bộ {report.event_denominator} đợt cạn, tỷ lệ là {report.early_numerator}/{report.event_denominator} ({percent(report.early_rate)}). Một đợt cạn bắt đầu khi tồn dương giảm về 0.</p>
      <p>Mỗi ngày nhìn trước {report.horizon_days} ngày. Thời gian giao hàng {report.lead_time_days} ngày, tồn đầu {report.cover_days} ngày phủ tính từ bình quân bán 28 ngày, hệ số an toàn {report.safety_multiplier}. Mỗi mặt hàng nhập cố định {report.fixed_order_qty} đơn vị mỗi lần. Kết quả tính trên kỳ hồi cứu đã xem.</p>
      <p>Bản ROP cố định trước đây đạt {percent(historical.early_rate)} ({historical.early_numerator}/{historical.event_denominator}). Các phiên bản dùng chính sách nhập khác nhau, nên đường tồn và số đợt cạn khác nhau.</p>
      <p>Chỉ số đánh giá khả năng cảnh báo cạn, không phải độ chính xác dự báo lượng bán hoặc hiệu quả vận hành thực tế. Không bật S25, không huấn luyện lại mô hình.</p>
    </details>
  </Panel>;
}
