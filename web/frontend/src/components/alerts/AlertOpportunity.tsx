import { useResource } from "../../hooks/useResource";
import { Panel } from "../ui/Panel";
import { Table } from "../ui/Table";
import { State } from "../ui/State";
import { type Run, type Row } from "../../types/api";
import { fmt, pct } from "../../utils/format";

export function AlertOpportunity({ run }: { run?: Run }) {
  const ready = run?.kind === "alert_replay" && run.status === "complete";
  const data = useResource<{ diagnostic: Row }>(
    ready ? `/runs/${run.id}/alert-opportunities` : null,
  );
  if (!ready) return null;
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
            Với các origin và tồn đầu của lượt này, trần lý thuyết là{" "}
            <strong>{pct(d.theoretical_max_early_rate)}</strong>; kết quả thực
            đạt <strong>{pct(d.observed_early_rate)}</strong>. Còn{" "}
            {fmt(d.missed_eligible_events)}/{fmt(d.eligible_early_events)} ca có
            đủ thời gian nhưng chưa được cảnh báo.
          </p>
          <p className="caption">
            Đây là giới hạn riêng của cách khởi tạo và cửa sổ replay hiện tại,
            không phải trần chất lượng của mọi hệ thống. Tỷ lệ chính thức vẫn
            giữ toàn bộ sự kiện tương lai trong mẫu số. Cần theo dõi từ trước
            hoặc kiểm tra tồn đầu/chính sách; thay kịch bản phải đánh giá lại,
            không bỏ các ca cạn sớm.
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
