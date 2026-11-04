import report from "../../data/c00-evaluation.json";
import reportUrl from "../../data/c00-evaluation.json?url";
import { fmt } from "../../utils/format";
import { Card } from "../ui/Card";
import { Panel } from "../ui/Panel";

const percent = (value: number) => `${fmt(value * 100, 2)}%`;

export function C00Evaluation() {
  return <Panel title="Đánh giá C00 — hồi cứu toàn kỳ"
    note="Kết quả đã chạy lại và kiểm chứng độc lập trên bộ đầu vào, dự báo và chính sách đã chốt."
    action={<a className="button secondary" href={reportUrl} download="C00-hoi-cuu-2025.json">Tải kết quả C00</a>}>
    <p>Kỳ đánh giá: <strong>{report.score_start.split("-").reverse().join("/")} – {report.score_end.split("-").reverse().join("/")}</strong> · {fmt(report.policy_count)} mặt hàng · Cảnh báo trước ít nhất {report.minimum_lead_days} ngày.</p>
    <div className="stats">
      <Card label="C00 · Báo sớm ≥7 ngày" value={percent(report.early_rate)}
        note={`${report.early_numerator}/${report.event_denominator} đợt cạn được báo sớm`} />
      <Card label="Precision cảnh báo" value={percent(report.precision)} note={`${fmt(report.alarm_tp)} đúng / ${fmt(report.alarm_fp)} sai, theo mặt hàng-ngày`} />
      <Card label="Recall theo đợt cạn" value={percent(report.recall)} note={`${report.matched_events}/${report.event_denominator} đợt cạn có cảnh báo`} />
      <Card label="Sai lệch ngày cạn trung bình" value={`${fmt(report.date_mae, 2)} ngày`} note={`Trên ${report.matched_events} đợt cạn có cảnh báo`} />
    </div>
    <p className="notice">Đây là kết quả nghiên cứu hồi cứu C00 với tự bổ sung hàng và {report.warmup_days} ngày khởi tạo. Kết quả cố định theo bộ dữ liệu đã chốt, không thay theo kịch bản hoặc bộ lọc đang chọn. Tỷ lệ của từng lượt Kiểm tra cảnh báo 14 ngày nằm trong phần Tóm tắt bên dưới.</p>
    <details className="advanced-section c00-evaluation-details">
      <summary>Cách tính và nguồn kết quả C00</summary>
      <p>Tỷ lệ báo sớm = {report.early_numerator}/{report.event_denominator} × 100% = {percent(report.early_rate)}. Một đợt cạn bắt đầu khi tồn dương giảm về 0; sau khi nhập lại, lần cạn tiếp theo là một đợt khác.</p>
      <p>Mỗi ngày nhìn trước {report.horizon_days} ngày, giữ nguyên C00; thời gian giao hàng {report.lead_time_days} ngày, tồn đầu {report.cover_days} ngày phủ, hệ số an toàn {report.safety_multiplier}. Chính sách ROP và lượng nhập cố định được áp hồi cứu; dữ liệu kỳ này đã được xem trước đây, không phải tập kiểm định mới.</p>
      <p>Chỉ số đánh giá khả năng cảnh báo cạn, không phải độ chính xác dự báo lượng bán hoặc hiệu quả vận hành thực tế. Không bật S25, không huấn luyện lại mô hình.</p>
    </details>
  </Panel>;
}
