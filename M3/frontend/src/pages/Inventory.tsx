import { useEffect, useState } from "react";
import {
  type Run,
  type Context,
  type Page,
  type Row,
  resultQuery,
  fmt,
  text,
} from "../api/client";
import {
  useResource,
  Panel,
  Table,
  Pager,
  State,
  ExportButton,
  Card,
  DetailDrawer,
  PlanRequired,
  badge,
} from "../components/common";
import { Icon } from "../components/Icon";
import type { WorkspaceData } from "./Overview";
export function Inventory({
  run,
  ctx,
  onChoose,
}: {
  run?: Run;
  ctx: Context;
  onChoose?: () => void;
}) {
  const [page, setPage] = useState(1),
    [status, setStatus] = useState(""),
    [selection, setSelection] = useState<{ key: string; row: Row }>();
  const key = JSON.stringify([ctx, status]);
  const focused = selection?.key === key ? selection.row : undefined;
  useEffect(() => setPage(1), [key]);
  const ready =
    run?.status === "complete" &&
    ["policy_replay", "alert_replay", "stock_projection"].includes(run.kind);
  const q = resultQuery(ctx, {
    date_from: ctx.origin,
    date_to: ctx.origin,
    page,
    page_size: 50,
    state: status,
  });
  const data = useResource<Page>(
    ready ? `/runs/${run.id}/inventory?${q}` : null,
  );
  const summary = useResource<WorkspaceData>(
    ready && ctx.origin
      ? `/runs/${run.id}/workspace?${resultQuery(ctx, { as_of_date: ctx.origin })}`
      : null,
  );
  const s = summary.data?.summary;
  const rows = data.data?.items ?? [];
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Tồn kho</h1>
          <p>
            Theo dõi từng mã SIM/gói data, so tồn hiện có với ngưỡng nhập và
            lượng hàng đang về.
          </p>
        </div>
        {ready && (
          <ExportButton url={`/runs/${run.id}/exports/inventory_daily?${q}`} />
        )}
      </div>
      {!ready ? (
        <PlanRequired onChoose={onChoose} />
      ) : (
        <>
          <div className="stats">
            <Card
              label="Mặt hàng đang quản lý"
              value={fmt(s?.item_count)}
              note="Theo kho, SKU và ngày đang chọn"
              icon="box"
            />
            <Card
              label="Tồn hiện có"
              value={fmt(s?.on_hand_units)}
              note="Chưa cộng lượng đang về"
              icon="grid"
            />
            <Card
              label="Dưới ngưỡng tồn"
              value={fmt(s?.low_stock_items)}
              note="Bao gồm các mặt hàng đã đặt đủ"
              icon="alert"
              tone="orange"
            />
            <Card
              label="Cần đặt thêm"
              value={fmt(s?.replenish_items)}
              note="Lượng đề xuất lớn hơn 0"
              icon="truck"
              tone="teal"
            />
          </div>
          <State loading={summary.loading} error={summary.error} />
          <Panel
            title="Danh sách tồn kho"
            note={`Ngày ${ctx.origin} · Nhấn một mặt hàng để xem chi tiết.`}
            action={
              <select
                aria-label="Trạng thái tồn kho"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="">Tất cả trạng thái</option>
                <option value="low_stock">Cần đặt thêm</option>
                <option value="pending_covers">Đã có đủ hàng đang về</option>
              </select>
            }
          >
            <State
              loading={data.loading}
              error={data.error}
              empty={!data.loading && !data.error && !rows.length}
            />
            {!data.loading && !data.error && rows.length > 0 && (
              <Table
                rows={rows}
                onRow={(row) => setSelection({ key, row })}
                columns={[
                  {
                    key: "sku",
                    label: "Mặt hàng",
                    render: (v, r) => (
                      <div className="cell-product">
                        <strong>{String(v)}</strong>
                        <small>{String(r.product_type)}</small>
                      </div>
                    ),
                  },
                  {
                    key: "carrier",
                    label: "Kho / tuyến",
                    render: (v, r) => (
                      <div className="cell-product">
                        <strong>{String(v)}</strong>
                        <small>{String(r.destination_country)}</small>
                      </div>
                    ),
                  },
                  { key: "closing_qty", label: "Tồn hiện có" },
                  { key: "rop", label: "Ngưỡng nhập" },
                  { key: "pending_qty", label: "Đang về" },
                  {
                    key: "recommended_qty",
                    label: "Cần đặt",
                    render: (v) => (
                      <span className="quantity-emphasis">{fmt(v)}</span>
                    ),
                  },
                  {
                    key: "needs_replenishment",
                    label: "Trạng thái",
                    render: (v, r) =>
                      badge(
                        v
                          ? Number(r.recommended_qty) > 0
                            ? "low_stock"
                            : "pending_covers"
                          : "sufficient",
                      ),
                  },
                  {
                    key: "item_id",
                    label: "",
                    render: () => <Icon name="chevron" size={15} />,
                  },
                ]}
              />
            )}
            <Pager
              page={page}
              total={data.data?.total ?? 0}
              onChange={setPage}
            />
          </Panel>
          {run.kind === "stock_projection" && (
            <p className="caption">
              Số tồn tại mốc chốt được khởi tạo theo phương án mô phỏng. Các
              ngày sau mốc chốt là dự kiến; chưa ghi nhận là tồn thực tế.
            </p>
          )}
        </>
      )}
      {focused && (
        <DetailDrawer
          title={text(focused.sku)}
          onClose={() => setSelection(undefined)}
        >
          <dl className="drawer-fields">
            <div>
              <dt>Kho / tuyến</dt>
              <dd>
                {text(focused.destination_country)} / {text(focused.carrier)}
              </dd>
            </div>
            <div>
              <dt>Loại sản phẩm</dt>
              <dd>{text(focused.product_type)}</dd>
            </div>
            <div>
              <dt>Ngày sổ tồn</dt>
              <dd>{text(focused.date)}</dd>
            </div>
            <div>
              <dt>Trạng thái</dt>
              <dd>
                {badge(
                  focused.needs_replenishment
                    ? Number(focused.recommended_qty) > 0
                      ? "low_stock"
                      : "pending_covers"
                    : "sufficient",
                )}
              </dd>
            </div>
          </dl>
          <div className="stats">
            <Card label="Tồn hiện có" value={fmt(focused.closing_qty)} />
            <Card label="Hàng đang về" value={fmt(focused.pending_qty)} />
            <Card label="Ngưỡng nhập" value={fmt(focused.rop)} />
            <Card
              label="Lượng cần đặt"
              value={fmt(focused.recommended_qty)}
              tone="orange"
            />
          </div>
          <h2>Chính sách nhập hàng</h2>
          <dl className="drawer-fields">
            <div>
              <dt>Tồn an toàn</dt>
              <dd>{fmt(focused.ss)}</dd>
            </div>
            <div>
              <dt>MOQ</dt>
              <dd>{fmt(focused.moq)}</dd>
            </div>
            <div>
              <dt>ROP tối thiểu</dt>
              <dd>{fmt(focused.configured_rop_floor)}</dd>
            </div>
            <div>
              <dt>Vị thế tồn IP</dt>
              <dd>{fmt(focused.inventory_position)}</dd>
            </div>
            <div>
              <dt>Mức tồn mục tiêu S</dt>
              <dd>{fmt(focused.target_stock)}</dd>
            </div>
            <div>
              <dt>ETA nếu đặt</dt>
              <dd>{text(focused.eta_if_ordered)}</dd>
            </div>
          </dl>
          <details className="advanced-section">
            <summary>Chi tiết sổ tồn & cách tính</summary>
            <div className="drawer-body">
              <Table
                rows={[focused]}
                columns={[
                  { key: "opening_qty", label: "Đầu ngày" },
                  { key: "receipts_qty", label: "Nhận" },
                  { key: "sales_qty", label: "Bán" },
                  { key: "fulfilled_qty", label: "Đáp ứng" },
                  { key: "shortage_qty", label: "Thiếu" },
                  { key: "closing_qty", label: "Cuối ngày" },
                ]}
              />
              <div className="formula">
                <span>
                  ROP = max({fmt(focused.rop_forecast)},{" "}
                  {fmt(focused.configured_rop_floor)})
                </span>
                <span>
                  IP = tồn cuối + đang về = {fmt(focused.inventory_position)}
                </span>
                <span>MOQ chỉ áp dụng khi cần đặt thêm.</span>
              </div>
              <p className="caption">
                Chỉ đề xuất khi tồn cuối &lt; ROP. Có thể Q=0 khi hàng đang về
                đủ mức mục tiêu. Policy v{text(focused.policy_version)} ·
                L7/R1/H14.
              </p>
            </div>
          </details>
        </DetailDrawer>
      )}
    </>
  );
}
