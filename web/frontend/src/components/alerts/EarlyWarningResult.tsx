import type { Row, Run } from "../../types/api";
import { fmt, num, pct } from "../../utils/format";
import { isTradeRun } from "../../utils/trade";
import { Card } from "../ui/Card";
import { Panel } from "../ui/Panel";

export function EarlyWarningResult({ run, replay, onOpenReplay }: {
  run: Run; replay?: Run; onOpenReplay?: () => void;
}) {
  const evaluation = run.kind === "alert_replay" ? run : replay;
  const metrics = evaluation?.kind === "alert_replay" && evaluation.status === "complete"
    ? evaluation.result_summary.alert_metrics as Row | null | undefined : undefined;
  const related = !!metrics && evaluation?.id !== run.id;
  const denominator = num(metrics?.event_denominator);
  const numerator = num(metrics?.early_numerator);
  const rate = num(metrics?.early_rate);
  const measured = denominator !== null && denominator > 0 && numerator !== null && numerator >= 0 &&
    numerator <= denominator && rate !== null && rate >= 0 && rate <= 1 && Math.abs(rate - numerator / denominator) < 1e-8;
  return <Panel title="Kết quả cảnh báo sớm trước ít nhất 7 ngày"
    note="Đánh giá hồi cứu cảnh báo cạn hàng; không phải phần trăm chính xác của dự báo lượng bán.">
    {!metrics ? <>
      <p className="notice">Lượt này chưa có tỷ lệ cảnh báo sớm đã đánh giá. Chỉ số được đo bằng lượt Kiểm tra cảnh báo có đối chiếu sự kiện cạn trong hồi cứu; không suy ra từ số cảnh báo đang hiển thị.</p>
      {replay && onOpenReplay && <>
        <p>Có lượt Kiểm tra cảnh báo đã hoàn tất của cùng phiên bản kịch bản và cùng nguồn/dự báo cha. Kỳ hồi cứu: {replay.period_start} đến {replay.period_end}.</p>
        <button type="button" className="secondary" onClick={onOpenReplay}>Xem tỷ lệ của lượt Kiểm tra cảnh báo</button>
      </>}
    </> : <>
      {related && <p className="notice">Kết quả của lượt Kiểm tra cảnh báo {evaluation!.id.slice(0, 8)} cùng phiên bản kịch bản và cùng nguồn/dự báo cha. Đây là kỳ đánh giá đã có, chưa phải tỷ lệ đo riêng cho lượt {run.id.slice(0, 8)} tại ngày {run.as_of_date}.</p>}
      <p className="caption">Kỳ hồi cứu: {evaluation?.period_start ?? "—"} đến {evaluation?.period_end ?? "—"}. Số liệu toàn lượt kiểm tra cảnh báo này; bộ lọc kho, ngày và bảng không thay mẫu số.</p>
      <div className="stats">
        <Card label="Báo sớm ≥7 ngày" value={measured ? pct(rate) : "Chưa xác định"}
          note={`${fmt(numerator)}/${fmt(denominator)} sự kiện cạn đủ điều kiện`} />
        <Card label="Precision cảnh báo" value={pct(num(metrics.precision))} note="Tỷ lệ cảnh báo có sự kiện cạn tương ứng" />
        <Card label="Recall cảnh báo" value={pct(num(metrics.recall))} note="Tỷ lệ sự kiện cạn được phát hiện, gồm cả báo muộn" />
        <Card label="Ca không chấm" value={fmt(num(metrics.excluded_count))} note="Đã cạn tại mốc hoặc không đủ điều kiện đánh giá" />
      </div>
      {!measured && <p className="notice">{denominator === 0 ? "Không có sự kiện cạn đủ điều kiện trong lượt này; tỷ lệ chưa xác định, không phải 0%." : "Chưa có đủ dữ liệu hợp lệ để hiển thị tỷ lệ cảnh báo sớm."}</p>}
      <p className="caption">Tỷ lệ = số sự kiện cạn được cảnh báo khi còn ít nhất 7 ngày / tổng sự kiện cạn đủ điều kiện × 100%. Mẫu số vẫn gồm ca báo muộn và ca bỏ sót, kể cả các ca cạn ở D+1…D+6.</p>
      {evaluation && isTradeRun(evaluation) && Number(evaluation.result_summary.excluded_item_windows ?? 0) > 0 && <p className="notice">
        Không chấm {fmt(evaluation.result_summary.excluded_item_windows)} cửa sổ sản phẩm có hạn chế bán; không coi lượng bị chặn là thiếu hàng hoặc dùng việc giảm mẫu số để kết luận chất lượng tốt hơn.
      </p>}
      {related && onOpenReplay && <button type="button" className="text-button" onClick={onOpenReplay}>Mở lượt Kiểm tra cảnh báo này</button>}
    </>}
  </Panel>;
}
