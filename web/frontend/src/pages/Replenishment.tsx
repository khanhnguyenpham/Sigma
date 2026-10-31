import { PurchasingDetails } from "../components/purchasing/PurchasingDetails";
import { type PurchasingView } from "../types/context";
import { useEffect, useState } from "react";
import { type Run, type Page, type Row } from "../types/api";
import { type Context } from "../types/context";
import { resultQuery } from "../utils/url";
import { fmt, text } from "../utils/format";
import { useResource } from "../hooks/useResource";
import { Panel } from "../components/ui/Panel";
import { State } from "../components/ui/State";
import { Table } from "../components/ui/Table";
import { Pager } from "../components/ui/Pager";
import { ExportButton } from "../components/ui/ExportButton";
import { badge } from "../components/ui/Badge";
import { PlanRequired } from "../components/ui/PlanRequired";
import { Card } from "../components/ui/Card";

import { Icon } from "../components/ui/Icon";
import { warehouseName } from "../utils/warehouse";

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
                  key: "city",
                  label: "Kho nhận hàng",
                  render: (_v, r) => (
                    <div className="cell-product">
                      <strong>{warehouseName(r)}</strong>
                      <small>{String(r.destination_country)}</small>
                    </div>
                  ),
                },
                { key: "carrier", label: "Nhà mạng" },
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
        <PurchasingDetails
          focused={focused}
          onClose={() => setSelection(undefined)}
          onItem={onItem}
          view={view}
          data={data}
          selectView={selectView}
        />
      )}
    </>
  );
}
