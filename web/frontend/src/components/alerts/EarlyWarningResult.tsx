import type { Row, Run } from "../../types/api";
import { fmt, num, pct } from "../../utils/format";
import { isTradeRun } from "../../utils/trade";
import { Card } from "../ui/Card";
import { Panel } from "../ui/Panel";
import { State } from "../ui/State";
import { EligibleEarlyWarningCard, useAlertOpportunity } from "./AlertOpportunity";
import { useResource } from "../../hooks/useResource";

function PurchasingWarningResult({ run }: { run: Run }) {
  const result = useResource<{ diagnostic: Row }>(
    run.status === "complete" ? `/runs/${run.id}/policy-alert-evaluation` : null,
  );
  const diagnostic = result.data?.diagnostic;
  return <Panel title="Kết quả cảnh báo sớm của kế hoạch nhập hàng"
    note={`Lượt ${run.id.slice(0, 8)} · ${run.period_start ?? "—"} đến ${run.period_end ?? "—"}`}>
    <State loading={result.loading} error={result.error} />
    {run.status !== "complete" && <p className="notice">Kết quả có sau khi lượt chạy hoàn tất.</p>}
    {diagnostic && <>
      <div className="stats">
        <EligibleEarlyWarningCard diagnostic={diagnostic} />
        <Card label="Recall cảnh báo" value={pct(diagnostic.recall)}
          note={`${fmt(diagnostic.detected_events)}/${fmt(diagnostic.event_denominator)} đợt cạn có cảnh báo`} />
      </div>
      <p className="caption">Mẫu số báo sớm gồm các đợt cạn có ít nhất một ngày còn hàng để cảnh báo trước 7–14 ngày. Tỷ lệ trên toàn bộ đợt cạn là {pct(diagnostic.observed_early_rate)} ({fmt(diagnostic.observed_early_numerator)}/{fmt(diagnostic.event_denominator)}).</p>
      {Number(diagnostic.blocked_sales_item_days) > 0 && <p className="caption">
        Nhà mạng chặn bán trong {fmt(diagnostic.blocked_sales_item_days)} mặt hàng-ngày. Có {fmt(diagnostic.warnings_with_sales_block)} cảnh báo chưa gặp đợt cạn trước khi bị gián đoạn theo dõi do chặn bán.
      </p>}
      <p className="caption">Trong các cảnh báo chưa ghi nhận cạn, {fmt(diagnostic.warnings_with_receipt)} cảnh báo có lô mới về trong thời gian theo dõi và {fmt(diagnostic.warnings_with_incomplete_followup)} cảnh báo chưa đủ 14 ngày theo dõi.</p>
    </>}
  </Panel>;
}

export function EarlyWarningResult({ run }: { run: Run }) {
  const metrics = run.kind === "alert_replay" && run.status === "complete"
    ? run.result_summary.alert_metrics as Row | null | undefined : undefined;
  const opportunities = useAlertOpportunity(metrics ? run : undefined);
  const diagnostic = opportunities.data?.diagnostic;
  if (run.kind === "policy_replay") return <PurchasingWarningResult run={run} />;
  return <Panel title="Kết quả kiểm tra cảnh báo"
    note={`Kỳ hồi cứu UTC · ${run.period_start ?? "—"} đến ${run.period_end ?? "—"}`}>
    {!metrics ? <p className="notice">Lượt này chưa có kết quả chấm cảnh báo cạn hàng.</p> : <>
      <State loading={opportunities.loading} error={opportunities.error} />
      <div className="stats">
        <EligibleEarlyWarningCard diagnostic={diagnostic} />
        <Card label="Precision cảnh báo" value={pct(num(metrics.precision))} note="Tỷ lệ cảnh báo có sự kiện cạn tương ứng" />
        <Card label="Recall cảnh báo" value={pct(num(metrics.recall))} note="Tỷ lệ sự kiện cạn được phát hiện, gồm cả báo muộn" />
        <Card label="Ca không chấm" value={fmt(num(metrics.excluded_count))} note="Đã cạn tại mốc hoặc không đủ điều kiện đánh giá" />
      </div>
      {diagnostic?.eligible_early_events === 0 && <p className="notice">Không có sự kiện cạn đủ thời gian báo trước 7 ngày trong lượt này.</p>}
      <p className="caption">Mẫu số gồm các ca cạn từ D+7 đến D+14, kể cả ca bị bỏ sót.</p>
      {diagnostic && <p className="caption">Cạn ở D+1 đến D+6: {fmt(diagnostic.short_notice_events)} ca. Tỷ lệ trên toàn bộ ca cạn: {pct(diagnostic.observed_early_rate)} ({fmt(diagnostic.observed_early_numerator)}/{fmt(diagnostic.event_denominator)}).</p>}
      {isTradeRun(run) && Number(run.result_summary.excluded_item_windows ?? 0) > 0 && <p className="notice">
        Loại {fmt(run.result_summary.excluded_item_windows)} cửa sổ sản phẩm có hạn chế bán khỏi phép chấm cảnh báo cạn hàng.
      </p>}
    </>}
  </Panel>;
}
