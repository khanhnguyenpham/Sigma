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
  State,
  Table,
  Pager,
  ExportButton,
  badge,
  PlanRequired,
  Card,
  DetailDrawer,
} from "../components/common";
import { Icon } from "../components/Icon";
export type PurchasingView = "recommendations" | "incoming" | "history";
interface PurchasingData extends Page {
  summary: Row;
}
export function Replenishment({
  run,
  ctx,
  onChoose,
  view: controlledView,
  onViewChange,
  onItem,
}: {
  run?: Run;
  ctx: Context;
  onChoose?: () => void;
  view?: PurchasingView;
  onViewChange?: (view: PurchasingView) => void;
  onItem?: (row: Row, page?: string, view?: PurchasingView) => void;
}) {
  const [localView, setLocalView] = useState<PurchasingView>("recommendations"),
    [page, setPage] = useState(1),
    [term, setTerm] = useState(""),
    [search, setSearch] = useState(""),
    [sort, setSort] = useState("quantity_desc"),
    [selection, setSelection] = useState<{ key: string; row: Row }>();
  const view = controlledView ?? localView;
  useEffect(() => {
    const timer = setTimeout(() => setSearch(term), 250);
    return () => clearTimeout(timer);
  }, [term]);
  useEffect(() => {
    setSort(
      view === "incoming"
        ? "eta_asc"
        : view === "history"
          ? "ordered_desc"
          : "quantity_desc",
    );
  }, [view]);
  const key = JSON.stringify([ctx, view, term, sort]);
  const focused = selection?.key === key ? selection.row : undefined;
  useEffect(() => setPage(1), [key]);
  const ready =
    run?.status === "complete" &&
    run.result_summary.inventory_available !== false &&
    ["policy_replay", "alert_replay", "stock_projection"].includes(run.kind);
  const appliedSort =
    view === "recommendations" && sort === "ordered_desc"
      ? "quantity_desc"
      : sort;
  const q = resultQuery(ctx, {
    as_of_date: ctx.origin,
    view,
    search,
    sort: appliedSort,
    page,
    page_size: 50,
  });
  const resource = useResource<PurchasingData>(
    ready && ctx.origin ? `/runs/${run.id}/purchasing?${q}` : null,
  );
  const typing = term !== search;
  const data = typing ? undefined : resource.data;
  const rows = data?.items ?? [],
    s = data?.summary;
  function selectView(value: PurchasingView) {
    setSort(
      value === "incoming"
        ? "eta_asc"
        : value === "history"
          ? "ordered_desc"
          : "quantity_desc",
    );
    setLocalView(value);
    onViewChange?.(value);
    setPage(1);
    setSelection(undefined);
  }
  const tabs: [PurchasingView, string, string][] = [
    ["recommendations", "Cần bổ sung", "recommended_items"],
    ["incoming", "Đang về", "incoming_lots"],
    ["history", "Lịch sử lô nhập", "historical_lots"],
  ];
  return (
    <>
      <div className="page-heading">
        <div>
          <h1>Kế hoạch nhập hàng</h1>
          <p>
            Rà soát nhu cầu bổ sung và theo dõi các lô hàng theo ngày kế hoạch.
          </p>
        </div>
        {ready && !typing && (
          <ExportButton url={`/runs/${run.id}/purchasing/export?${q}`} />
        )}
      </div>
      {!ready ? (
        <PlanRequired onChoose={onChoose} />
      ) : (
        <>
          <div className="stats purchase-stats">
            <Card
              label="Cần đặt thêm"
              value={fmt(s?.recommended_items)}
              note={
                s
                  ? `${fmt(s.recommended_units)} đơn vị đề xuất`
                  : "Theo bộ lọc đang chọn"
              }
              icon="truck"
              tone="orange"
            />
            <Card
              label="Lô hàng đang về"
              value={fmt(s?.incoming_lots)}
              note={
                s
                  ? `${fmt(s.pending_units)} đơn vị đã đặt`
                  : "Chưa cộng vào tồn hiện có"
              }
              icon="clock"
              tone="teal"
            />
            <Card
              label="Lô nhập đã ghi nhận"
              value={fmt(s?.historical_lots)}
              note="Chỉ những lô đã đặt tại mốc dữ liệu"
              icon="box"
            />
          </div>
          {data?.context?.known_orders_through !== undefined &&
            data.context.known_orders_through !== ctx.origin && (
              <div className="notice">
                Thông tin lô nhập được chốt tại{" "}
                {text(data.context.known_orders_through)}. Chưa xác nhận nhận
                hàng sau mốc này.
              </div>
            )}
          {s && !s.inventory_available && view === "recommendations" && (
            <div className="notice">
              Không có sổ tồn phù hợp ngày và bộ lọc hiện tại để lập đề xuất.
              Hãy đổi ngày, bộ lọc hoặc tạo kế hoạch mới.
            </div>
          )}
          <Panel
            title="Danh sách nhập hàng"
            note={`Ngày kế hoạch ${ctx.origin} · UTC`}
          >
            <div
              className="work-tabs"
              role="group"
              aria-label="Danh sách nhập hàng"
            >
              {tabs.map(([id, title, count]) => (
                <button
                  key={id}
                  className={view === id ? "active" : ""}
                  aria-pressed={view === id}
                  onClick={() => selectView(id)}
                >
                  {title}
                  <span>{fmt(s?.[count])}</span>
                </button>
              ))}
            </div>
            <div className="list-toolbar">
              <label className="list-search">
                <Icon name="search" size={17} />
                <input
                  type="search"
                  aria-label="Tìm trong danh sách nhập hàng"
                  placeholder="Tìm mã sản phẩm, nhà mạng, quốc gia…"
                  value={term}
                  maxLength={80}
                  onChange={(e) => setTerm(e.target.value)}
                />
                {term && (
                  <button
                    className="icon-button"
                    aria-label="Xóa tìm kiếm"
                    onClick={() => setTerm("")}
                  >
                    <Icon name="close" size={15} />
                  </button>
                )}
              </label>
              <label className="sort-control">
                Sắp xếp
                <select
                  aria-label="Sắp xếp nhập hàng"
                  value={appliedSort}
                  onChange={(e) => setSort(e.target.value)}
                >
                  <option value="quantity_desc">Số lượng giảm dần</option>
                  <option value="quantity_asc">Số lượng tăng dần</option>
                  <option value="eta_asc">Ngày nhận gần nhất</option>
                  {view !== "recommendations" && (
                    <option value="ordered_desc">Đặt gần đây nhất</option>
                  )}
                </select>
              </label>
            </div>
            <State
              loading={typing || resource.loading}
              error={resource.error}
              empty={
                !typing && !resource.loading && !resource.error && !rows.length
              }
            />
            <Table
              rows={rows}
              onRow={(row) => setSelection({ key, row })}
              columns={[
                ...(view !== "recommendations"
                  ? [
                      {
                        key: "id",
                        label: "Mã lô",
                        render: (v: unknown) => (
                          <span className="record-ref">Lô #{String(v)}</span>
                        ),
                      },
                    ]
                  : []),
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
                ...(view === "recommendations"
                  ? [
                      { key: "closing_qty", label: "Tồn hiện có" },
                      { key: "pending_qty", label: "Đang về" },
                      { key: "rop", label: "Ngưỡng nhập" },
                      {
                        key: "recommended_qty",
                        label: "Cần đặt",
                        render: (v: unknown) => (
                          <strong className="quantity-emphasis">
                            {fmt(v)}
                          </strong>
                        ),
                      },
                      { key: "eta_if_ordered", label: "Nhận nếu đặt tại mốc" },
                    ]
                  : [
                      { key: "ordered_qty", label: "Số lượng" },
                      { key: "ordered_on", label: "Ngày đặt" },
                      { key: "eta", label: "Dự kiến nhận" },
                      { key: "status", label: "Trạng thái", render: badge },
                    ]),
                {
                  key: "detail",
                  label: "",
                  render: () => <Icon name="chevron" size={15} />,
                },
              ]}
            />
            {data && (
              <Pager page={page} total={data.total} onChange={setPage} />
            )}
            <p className="caption">
              Nhấn một dòng để xem chi tiết. CSV xuất toàn bộ kết quả theo tìm
              kiếm và bộ lọc. Đề xuất nhập chưa tạo đơn đặt hàng.
            </p>
          </Panel>
        </>
      )}
      {focused && (
        <DetailDrawer
          eyebrow={
            view === "recommendations"
              ? "Đề xuất nhập hàng"
              : "Chi tiết lô nhập"
          }
          title={
            view === "recommendations"
              ? String(focused.sku)
              : `Lô #${focused.id}`
          }
          onClose={() => setSelection(undefined)}
        >
          <div className="detail-product">
            <span className="detail-product-icon">
              <Icon name={view === "recommendations" ? "box" : "truck"} />
            </span>
            <div>
              <strong>{text(focused.sku)}</strong>
              <p>
                {text(focused.carrier)} · {text(focused.destination_country)} ·{" "}
                {text(focused.product_type)}
              </p>
            </div>
          </div>
          {view === "recommendations" ? (
            <>
              <div className="decision-callout">
                <span>Đề xuất bổ sung</span>
                <strong>
                  {fmt(focused.recommended_qty)} <small>đơn vị</small>
                </strong>
                <p>
                  Tồn {fmt(focused.closing_qty)} thấp hơn ngưỡng{" "}
                  {fmt(focused.rop)}. Lượng đặt đã tính hàng đang về và lượng
                  đặt tối thiểu.
                </p>
              </div>
              <dl className="drawer-fields">
                <div>
                  <dt>Tồn hiện có</dt>
                  <dd>{fmt(focused.closing_qty)}</dd>
                </div>
                <div>
                  <dt>Hàng đang về</dt>
                  <dd>{fmt(focused.pending_qty)}</dd>
                </div>
                <div>
                  <dt>Vị thế tồn (IP)</dt>
                  <dd>{fmt(focused.inventory_position)}</dd>
                </div>
                <div>
                  <dt>Mức tồn mục tiêu</dt>
                  <dd>{fmt(focused.target_stock)}</dd>
                </div>
                <div>
                  <dt>Lượng đặt tối thiểu (MOQ)</dt>
                  <dd>{fmt(focused.moq)}</dd>
                </div>
                <div>
                  <dt>Nhận nếu đặt tại mốc</dt>
                  <dd>{text(focused.eta_if_ordered)}</dd>
                </div>
              </dl>
              <p className="caption">
                Đây là khuyến nghị trong kế hoạch mô phỏng, chưa phát sinh lô
                nhập hoặc gửi đơn cho nhà cung cấp.
              </p>
            </>
          ) : (
            <>
              <div className="lot-summary">
                {badge(focused.status)}
                <strong>
                  {fmt(focused.ordered_qty)} <small>đơn vị</small>
                </strong>
              </div>
              <div className="delivery-timeline">
                <div>
                  <i />
                  <span>Ngày đặt</span>
                  <strong>{text(focused.ordered_on)}</strong>
                </div>
                <div>
                  <i />
                  <span>Dự kiến nhận · sau 7 ngày</span>
                  <strong>{text(focused.eta)}</strong>
                </div>
              </div>
              <dl className="drawer-fields">
                <div>
                  <dt>Đã nhận tại mốc dữ liệu</dt>
                  <dd>{fmt(focused.received_qty)}</dd>
                </div>
                <div>
                  <dt>Nhà cung cấp</dt>
                  <dd>
                    {focused.supplier_id ? `NCC #${focused.supplier_id}` : "—"}
                  </dd>
                </div>
                <div>
                  <dt>Phiên bản chính sách</dt>
                  <dd>{text(focused.policy_version)}</dd>
                </div>
                <div>
                  <dt>Mốc dữ liệu</dt>
                  <dd>{text(data?.context?.known_orders_through)}</dd>
                </div>
              </dl>
            </>
          )}
          {onItem && (
            <div className="drawer-actions">
              <button
                className="primary"
                onClick={() => onItem(focused, "inventory")}
              >
                Mở hồ sơ tồn kho <Icon name="arrow" size={16} />
              </button>
              {view === "recommendations" && (
                <button
                  className="secondary"
                  onClick={() => {
                    setSelection(undefined);
                    selectView("incoming");
                  }}
                >
                  Xem hàng đang về
                </button>
              )}
            </div>
          )}
        </DetailDrawer>
      )}
    </>
  );
}
