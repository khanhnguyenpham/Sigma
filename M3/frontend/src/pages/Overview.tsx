import { Card, Panel, Table, badge, State } from "../components/common";
import { fmt, pct, label, type Run, type Row } from "../api/client";
export function Overview({
  run,
  runs,
  onRun,
  onCreate,
}: {
  run?: Run;
  runs: Run[];
  onRun: (id: string) => void;
  onCreate: () => void;
}) {
  const s = run?.result_summary ?? {};
  const a = s.alert_metrics as Row | undefined;
  const complete = run?.status === "complete";
  return (
    <>
      <div className="hero">
        <div>
          <span className="eyebrow">MỘT NGUỒN · MỘT LƯỢT CHẠY</span>
          <h1>
            Từ nhu cầu đến
            <br />
            quyết định nhập hàng.
          </h1>
          <p>
            Dự báo theo tuyến, theo dõi tồn theo mặt hàng và giải thích từng đề
            xuất trên cùng một kịch bản.
          </p>
          <button className="primary" onClick={onCreate}>
            ＋ Chạy một phương án
          </button>
        </div>
        <div className="hero-note">
          <span>H14</span>
          <strong>
            Hai khối tuần.
            <br />
            Một kế hoạch có thể kiểm chứng.
          </strong>
          <p>
            Nhập sau 7 ngày lịch UTC.
            <br />
            Kho, supplier và tồn đều có nhãn mô phỏng.
          </p>
        </div>
      </div>
      <p className="caption">
        Các chỉ số Tổng quan tính toàn bộ lượt chạy, không áp dụng bộ lọc mặt
        hàng ở thanh trên.
      </p>
      <div className="stats">
        <Card
          label="Tuyến trong lượt chạy"
          value={complete ? fmt(s.routes ?? 46) : "—"}
          note={
            run?.kind === "forecast"
              ? "10 tuyến M2 khóa · 36 tuyến mở rộng"
              : "46 kho mô phỏng theo tuyến"
          }
        />
        <Card
          label={a ? "Báo sớm ≥7 ngày" : "Tỷ lệ đáp ứng"}
          value={complete ? pct(a?.early_rate ?? s.fill_rate) : "—"}
          note={
            a
              ? `${fmt(a.early_numerator)}/${fmt(a.event_denominator)} sự kiện mô phỏng`
              : "Chỉ có khi replay chính sách có actual"
          }
          tone="teal"
        />
        <Card
          label="Lượng chưa đáp ứng"
          value={complete ? fmt(s.shortage_qty) : "—"}
          note="Không thay số bán gốc bằng lượng đáp ứng"
          tone="orange"
        />
        <Card
          label="Mặt hàng"
          value={complete ? fmt(s.items ?? 920) : "—"}
          note="Tuyến × SKU × loại sản phẩm"
        />
      </div>
      {run && run.status !== "complete" && (
        <div className="notice">
          {badge(run.status)}{" "}
          <strong>{String(s.phase ?? "Đang chuẩn bị")}</strong> ·{" "}
          {String(
            s.completed_jobs ?? s.completed_origins ?? s.completed_windows ?? 0,
          )}
          /{String(s.total_jobs ?? s.total_origins ?? s.total_windows ?? "…")} ·{" "}
          {run.error_code ?? "Tiến độ được cập nhật theo công việc thực."}
        </div>
      )}
      <div className="flow">
        <div>
          <b>01</b>
          <strong>Dự báo</strong>
          <p>Tổng 7 ngày và phân bổ ngày, theo từng tuyến.</p>
        </div>
        <div>
          <b>02</b>
          <strong>Tính tồn & nhập</strong>
          <p>ROP floor, safety, MOQ và hàng đang về.</p>
        </div>
        <div>
          <b>03</b>
          <strong>Theo dõi cảnh báo</strong>
          <p>Ngày cạn dự kiến và kết quả replay riêng.</p>
        </div>
      </div>
      <Panel
        title="Các lượt chạy"
        note="Chọn một lượt để giữ nguyên nguồn, dự báo cha và phiên bản cấu hình."
      >
        <Table
          rows={runs as unknown as Row[]}
          onRow={(r) => onRun(String(r.id))}
          columns={[
            { key: "kind", label: "Nội dung", render: (v) => label(String(v)) },
            { key: "as_of_date", label: "Mốc chốt UTC" },
            { key: "status", label: "Trạng thái", render: badge },
            {
              key: "created_at",
              label: "Tạo lúc",
              render: (v) => new Date(String(v)).toLocaleString("vi-VN"),
            },
            {
              key: "id",
              label: "Mã lượt",
              render: (v) => String(v).slice(0, 8),
            },
          ]}
        />
      </Panel>
      <div className="notice subtle">
        <strong>Đọc đúng kết quả.</strong> Đây là snapshot lịch sử 2024–2025. Dự
        báo tương lai sau 31/12/2025 chưa có actual. Kết quả tổng tuần không
        thay tiêu chí ngày R05; test M2 đã dùng hồi cứu, LG U+ được chọn sau
        test-sweep.
      </div>
    </>
  );
}
