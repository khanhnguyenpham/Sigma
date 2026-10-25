import { type WorkspaceData } from "../types/api";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { Card } from "../components/ui/Card";
import { Panel } from "../components/ui/Panel";
import { Table } from "../components/ui/Table";
import { badge } from "../components/ui/Badge";
import { State } from "../components/ui/State";
import { PlanRequired } from "../components/ui/PlanRequired";
import { useResource } from "../hooks/useResource";
import type { PurchasingView } from "../types/context";
import { Icon } from "../components/ui/Icon";
import { fmt } from "../utils/format";
import { label } from "../utils/labels";
import { resultQuery } from "../utils/url";
import { type Run, type Row } from "../types/api";
import { type Context } from "../types/context";


export function Overview({
  run,
  ctx,
  runs,
  onRun,
  onCreate,
  onNavigate,
  onItem,
  onChoose,
}: {
  run?: Run;
  ctx: Context;
  runs: Run[];
  onRun: (id: string) => void;
  onCreate: () => void;
  onNavigate: (page: string, view?: PurchasingView) => void;
  onItem: (row: Row, page?: string) => void;
  onChoose?: () => void;
}) {
  const ready =
    run?.status === "complete" &&
    run.result_summary.inventory_available !== false &&
    ["stock_projection", "policy_replay", "alert_replay"].includes(run.kind);
  const resource = useResource<WorkspaceData>(
    ready && ctx.origin
      ? `/runs/${run.id}/workspace?${resultQuery(ctx, { as_of_date: ctx.origin })}`
      : null,
  );
  const s = resource.data?.summary;
  const terminal = run && ["failed", "invalidated"].includes(run.status);
  const jobs = run?.result_summary ?? {};
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Điều hành tồn kho</h1>
          <p>
            Theo dõi tồn, nhu cầu bổ sung và lịch hàng về trong ngày kế hoạch.
          </p>
        </div>
        <button className="secondary" onClick={() => onNavigate("inventory")}>
          Xem tồn kho <Icon name="arrow" size={16} />
        </button>
      </div>
      {run && run.status !== "complete" && (
        <div
          className={"job-status " + (terminal ? "job-error" : "")}
          role="status"
        >
          <div className="job-icon">
            <Icon name={terminal ? "alert" : "refresh"} />
          </div>
          <div>
            <strong>
              {terminal
                ? "Phương án chưa thể hoàn tất"
                : "Đang xử lý phương án"}
            </strong>
            <p>
              {terminal
                ? "Kiểm tra cấu hình và tạo lại phương án mới."
                : "Bạn có thể tiếp tục làm việc; kết quả sẽ cập nhật khi xử lý xong."}
            </p>
            <details>
              <summary>Chi tiết xử lý</summary>
              <p>
                {String(jobs.phase ?? run.status)} ·{" "}
                {String(
                  jobs.completed_jobs ??
                    jobs.completed_origins ??
                    jobs.completed_windows ??
                    0,
                )}
                /
                {String(
                  jobs.total_jobs ??
                    jobs.total_origins ??
                    jobs.total_windows ??
                    "…",
                )}{" "}
                · {run.error_code ?? ""}
              </p>
            </details>
          </div>
        </div>
      )}
      {!ready ? (
        run?.status === "complete" ? (
          <PlanRequired onChoose={onChoose} />
        ) : !run ? (
          <div className="empty-state">
            <Icon name="box" size={30} />
            <h2>Chưa có kế hoạch</h2>
            <p>
              Tạo phương án từ nguồn và dự báo đã có để bắt đầu quản lý tồn.
            </p>
            <button className="primary" onClick={onCreate}>
              <Icon name="plus" size={16} />
              Tạo phương án
            </button>
          </div>
        ) : null
      ) : (
        <>
          <State loading={resource.loading} error={resource.error} />
          <div className="stats">
            <Card
              label="Tồn hiện có"
              value={fmt(s?.on_hand_units)}
              note={
                s
                  ? fmt(s.item_count) + " mặt hàng trong bộ lọc"
                  : "Đang tải số liệu"
              }
              icon="box"
            />
            <Card
              label="Cần bổ sung"
              value={fmt(s?.replenish_items)}
              note={s ? fmt(s.recommended_units) + " đơn vị đề xuất nhập" : "—"}
              tone="orange"
              icon="truck"
            />
            <Card
              label="Lô hàng đang về"
              value={fmt(s?.incoming_lots)}
              note={s ? fmt(s.pending_units) + " đơn vị đã đặt" : "—"}
              tone="teal"
              icon="clock"
            />
            <Card
              label="Cảnh báo cần xử lý"
              value={fmt(s?.urgent_items)}
              note="Có nguy cơ cạn dưới 7 ngày hoặc đã cạn"
              tone="red"
              icon="bell"
            />
          </div>
          {s && !s.inventory_available && (
            <div className="notice">
              Phương án này không có sổ tồn tại ngày đang chọn. Hãy chọn ngày có
              dữ liệu hoặc tạo dự phóng tồn mới.
            </div>
          )}
          <div className="dashboard-grid">
            <Panel
              title="Mặt hàng cần bổ sung"
              note="Sắp xếp theo lượng cần nhập, áp dụng bộ lọc đang chọn."
              action={
                <button
                  className="text-button"
                  onClick={() => onNavigate("replenishment")}
                >
                  Xem tất cả <Icon name="arrow" size={15} />
                </button>
              }
            >
              {!resource.loading &&
                !resource.error &&
                (resource.data?.attention.length ? (
                  <Table
                    rows={resource.data.attention}
                    onRow={(row) => onItem(row, "inventory")}
                    columns={[
                      {
                        key: "sku",
                        label: "Mặt hàng",
                        render: (v, r) => (
                          <div className="cell-product">
                            <strong>{String(v)}</strong>
                            <small>
                              {String(r.carrier)} · {String(r.product_type)}
                            </small>
                          </div>
                        ),
                      },
                      { key: "closing_qty", label: "Tồn" },
                      { key: "rop", label: "Ngưỡng" },
                      {
                        key: "recommended_qty",
                        label: "Cần nhập",
                        render: (v) => (
                          <span className="quantity-emphasis">{fmt(v)}</span>
                        ),
                      },
                      {
                        key: "needs_replenishment",
                        label: "",
                        render: () => badge("low_stock"),
                      },
                    ]}
                  />
                ) : (
                  <div className="panel-empty">
                    <Icon name="check" size={26} />
                    <strong>Không có mặt hàng cần đặt thêm</strong>
                    <span>
                      Lượng đặt đề xuất bằng 0 trong phạm vi đang xem.
                    </span>
                  </div>
                ))}
            </Panel>
            <Panel
              title="Tồn kho theo tuyến"
              note="8 tuyến có tồn nhiều nhất trong bộ lọc."
            >
              {!!resource.data?.route_stock.length && (
                <div className="chart">
                  <ResponsiveContainer width="100%" height={265}>
                    <BarChart
                      data={resource.data.route_stock.map((r) => ({
                        ...r,
                        route_label: r.carrier,
                      }))}
                      layout="vertical"
                      margin={{ left: 0, right: 20 }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        horizontal={false}
                        stroke="#edf0f5"
                      />
                      <XAxis
                        type="number"
                        tick={{ fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        type="category"
                        dataKey="route_label"
                        width={95}
                        tick={{ fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        formatter={(v) => fmt(v, 0)}
                        labelFormatter={(_, payload) =>
                          payload[0]?.payload?.destination_country +
                          " / " +
                          payload[0]?.payload?.carrier
                        }
                      />
                      <Bar
                        dataKey="closing_qty"
                        name="Tồn hiện có"
                        fill="#5667e8"
                        radius={[0, 4, 4, 0]}
                        maxBarSize={18}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
              {!resource.loading && !resource.data?.route_stock.length && (
                <div className="panel-empty">
                  <Icon name="chart" />
                  <span>Chưa có số liệu tồn để hiển thị.</span>
                </div>
              )}
            </Panel>
          </div>
          <div className="dashboard-bottom">
            <Panel
              title="Lịch hàng đang về"
              note={
                resource.data?.context.known_orders_through &&
                resource.data.context.known_orders_through !== ctx.origin
                  ? `Các lô đã biết tại mốc ${resource.data.context.known_orders_through}; chưa xác nhận thực nhận sau mốc này.`
                  : "Chỉ các lô đã đặt và chưa đến ETA tại mốc đang xem."
              }
              action={
                <button
                  className="text-button"
                  onClick={() => onNavigate("replenishment", "incoming")}
                >
                  Xem hàng đang về <Icon name="arrow" size={15} />
                </button>
              }
            >
              {!!resource.data?.incoming.length ? (
                <Table
                  rows={resource.data.incoming}
                  columns={[
                    { key: "sku", label: "Mặt hàng" },
                    { key: "carrier", label: "Nhà mạng" },
                    { key: "ordered_qty", label: "Số lượng" },
                    { key: "eta", label: "Dự kiến nhận" },
                    {
                      key: "status",
                      label: "",
                      render: () => badge("ordered"),
                    },
                  ]}
                />
              ) : (
                !resource.loading && (
                  <div className="panel-empty">
                    <Icon name="truck" />
                    <span>Không có lô hàng đang chờ về trong bộ lọc.</span>
                  </div>
                )
              )}
            </Panel>
            <section className="quick-actions">
              <h2>Thao tác nhanh</h2>
              <p>Chuẩn bị kế hoạch và theo dõi xử lý.</p>
              <button onClick={onCreate}>
                <span className="quick-icon">
                  <Icon name="plus" />
                </span>
                <span>
                  <strong>Tạo phương án mới</strong>
                  <small>Chọn dữ liệu và kịch bản</small>
                </span>
                <Icon name="chevron" size={16} />
              </button>
              <button onClick={() => onNavigate("alerts")}>
                <span className="quick-icon orange">
                  <Icon name="bell" />
                </span>
                <span>
                  <strong>Kiểm tra cảnh báo</strong>
                  <small>Ưu tiên các mặt hàng có nguy cơ</small>
                </span>
                <Icon name="chevron" size={16} />
              </button>
              <button onClick={() => onNavigate("configuration")}>
                <span className="quick-icon teal">
                  <Icon name="settings" />
                </span>
                <span>
                  <strong>Thiết lập nhập hàng</strong>
                  <small>ROP, MOQ và mức tồn an toàn</small>
                </span>
                <Icon name="chevron" size={16} />
              </button>
            </section>
          </div>
        </>
      )}
      <details className="history-section">
        <summary>
          <Icon name="clock" size={16} />
          Lịch sử xử lý <span>{runs.length} phương án</span>
        </summary>
        <Panel
          title="Các phương án gần đây"
          note="Mỗi phương án giữ riêng dữ liệu, dự báo và phiên bản cấu hình."
        >
          <Table
            rows={runs.slice(0, 8) as unknown as Row[]}
            onRow={(r) => onRun(String(r.id))}
            columns={[
              {
                key: "kind",
                label: "Công việc",
                render: (v) => label(String(v)),
              },
              { key: "as_of_date", label: "Mốc dữ liệu" },
              { key: "status", label: "Trạng thái", render: badge },
              {
                key: "created_at",
                label: "Tạo lúc",
                render: (v) => new Date(String(v)).toLocaleString("vi-VN"),
              },
            ]}
          />
        </Panel>
      </details>
    </>
  );
}
