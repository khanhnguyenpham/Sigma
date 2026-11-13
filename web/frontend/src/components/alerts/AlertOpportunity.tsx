import { useResource } from "../../hooks/useResource";
import { Panel } from "../ui/Panel";
import { Table } from "../ui/Table";
import { State } from "../ui/State";
import { type Run, type Row } from "../../types/api";
import { fmt, num, pct } from "../../utils/format";
import { Card } from "../ui/Card";

export function useAlertOpportunity(run?: Run) {
  const ready = run?.kind === "alert_replay" && run.status === "complete";
  return useResource<{ diagnostic: Row }>(
    ready ? `/runs/${run.id}/alert-opportunities` : null,
  );
}

export function EligibleEarlyWarningCard({ diagnostic }: { diagnostic?: Row }) {
  const numerator = num(diagnostic?.observed_early_numerator);
  const denominator = num(diagnostic?.eligible_early_events);
  const rate = num(diagnostic?.eligible_detection_rate);
  const measured = denominator !== null && denominator > 0 && numerator !== null &&
    numerator >= 0 && numerator <= denominator && rate !== null &&
    Math.abs(rate - numerator / denominator) < 1e-8;
  return <Card label="Báo sớm ≥7 ngày" value={measured ? pct(rate) : "Chưa xác định"}
    note={diagnostic ? `${fmt(numerator)}/${fmt(denominator)} ca có đủ thời gian báo sớm` : undefined} />;
}

export function AlertOpportunity({ data }: { data: ReturnType<typeof useAlertOpportunity> }) {
  const d = data.data?.diagnostic;
  return (
    <Panel
      title="Cơ hội báo trước 7 ngày trong lượt replay"
      note="Phân tích sau replay, toàn lượt; bộ lọc bảng không thay mẫu số. Không dùng actual này để tạo dự báo."
    >
      <State loading={data.loading} error={data.error} />
      {d && (
        <>
          <p>
            Trong {fmt(d.event_denominator)} sự kiện cạn, có{" "}
            <strong>{fmt(d.short_notice_events)}</strong> ca xảy ra ở D+1…D+6.
            Ngay tại origin đã không còn đủ 7 ngày để báo sớm.
          </p>
          <p>
            Nếu tính trên toàn bộ ca cạn, tỷ lệ báo sớm là{" "}
            <strong>{pct(d.observed_early_rate)}</strong> và tối đa có thể đạt{" "}
            <strong>{pct(d.theoretical_max_early_rate)}</strong> với các mốc bắt đầu của lượt này. Còn{" "}
            {fmt(d.missed_eligible_events)}/{fmt(d.eligible_early_events)} ca có
            đủ thời gian nhưng chưa được cảnh báo.
          </p>
          <p className="caption">
            Thẻ Báo sớm ≥7 ngày dùng các ca cạn từ D+7 đến D+14, kể cả ca bị bỏ sót.
          </p>
          <details>
            <summary>Xem phân bố thời điểm cạn thực mô phỏng</summary>
            <Table
              rows={d.histogram as Row[]}
              columns={[
                { key: "lead_days", label: "Ngày sau origin" },
                { key: "events", label: "Sự kiện cạn" },
                { key: "detected", label: "Có cảnh báo tại origin" },
              ]}
            />
          </details>
        </>
      )}
    </Panel>
  );
}
