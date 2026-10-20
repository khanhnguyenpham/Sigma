import { lazy, Suspense, useEffect, useState } from "react";
import {
  type Run,
  type Page,
  type Context,
  readContext,
  contextUrl,
  label,
  text,
} from "./api/client";
import { useResource, State, badge } from "./components/common";
import { Icon } from "./components/Icon";
import { RunDialog } from "./components/RunDialog";
const Overview = lazy(() =>
  import("./pages/Overview").then((m) => ({ default: m.Overview })),
);
import { Inventory } from "./pages/Inventory";
import { Replenishment } from "./pages/Replenishment";
import { Configuration } from "./pages/Configuration";
import "./styles.css";

const Forecast = lazy(() =>
  import("./pages/Forecast").then((m) => ({ default: m.Forecast })),
);
const Alerts = lazy(() =>
  import("./pages/Alerts").then((m) => ({ default: m.Alerts })),
);
const PAGES = [
  ["overview", "grid", "Tổng quan"],
  ["inventory", "box", "Tồn kho"],
  ["forecast", "chart", "Dự báo nhu cầu"],
  ["replenishment", "truck", "Nhập hàng"],
  ["alerts", "bell", "Cảnh báo"],
  ["configuration", "settings", "Cấu hình"],
];
const inventoryKinds = ["stock_projection", "policy_replay", "alert_replay"];

export default function App() {
  const [ctx, setCtx] = useState<Context>(readContext);
  const [page, setPage] = useState(location.hash.slice(1) || "overview");
  const [dialog, setDialog] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const runsResource = useResource<Page<Run>>(
    `/runs?page_size=100&refresh=${refresh}`,
    true,
  );
  const latest = runsResource.data?.items ?? [];
  const selectedResource = useResource<Run>(
    ctx.runId && latest.length && !latest.some((r) => r.id === ctx.runId)
      ? `/runs/${ctx.runId}`
      : null,
  );
  const runs =
    selectedResource.data &&
    !latest.some((r) => r.id === selectedResource.data?.id)
      ? [...latest, selectedResource.data]
      : latest;
  const run = runs.find((r) => r.id === ctx.runId);
  const catalog = useResource<Page>(
    run?.status === "complete"
      ? `/warehouses?run_id=${run.id}&page_size=100`
      : "/warehouses?page_size=100",
  );
  const items = useResource<Page>(
    ctx.warehouseId
      ? `/items?warehouse_id=${ctx.warehouseId}&page_size=100${run?.status === "complete" ? "&run_id=" + run.id : ""}`
      : null,
  );
  const suppliers = useResource<Page>("/suppliers?page_size=100");
  const hasWork = runs.some((r) => ["queued", "running"].includes(r.status));
  const compatible =
    runs.find(
      (r) =>
        r.status === "complete" &&
        r.kind === "stock_projection" &&
        r.as_of_date === "2025-10-31",
    ) ??
    runs.find(
      (r) => r.status === "complete" && inventoryKinds.includes(r.kind),
    );
  const busyRun = runs.find((r) => ["queued", "running"].includes(r.status));

  useEffect(() => {
    const timer = setInterval(
      () => setRefresh((v) => v + 1),
      hasWork ? 2000 : 15000,
    );
    return () => clearInterval(timer);
  }, [hasWork]);
  useEffect(() => {
    if (!ctx.runId && runs.length) {
      const preferred = compatible ?? runs.find((r) => r.status === "complete");
      if (preferred) selectRun(preferred.id);
    }
  }, [runsResource.data]);
  useEffect(() => {
    history.replaceState(null, "", "?" + contextUrl(ctx) + "#" + page);
  }, [ctx, page]);
  useEffect(() => {
    const pop = () => {
      setCtx(readContext());
      setPage(location.hash.slice(1) || "overview");
    };
    window.addEventListener("popstate", pop);
    return () => window.removeEventListener("popstate", pop);
  }, []);
  useEffect(() => {
    if (
      ctx.itemId &&
      items.data &&
      !items.data.items.some((i) => String(i.id) === ctx.itemId)
    )
      setCtx((c) => ({ ...c, itemId: "" }));
  }, [items.data]);
  useEffect(() => {
    if (run && !ctx.origin)
      setCtx((c) => ({
        ...c,
        origin: run.kind === "forecast" ? "2025-10-31" : run.as_of_date,
      }));
  }, [run?.id, ctx.origin]);
  function selectRun(id: string) {
    const r = runs.find((r) => r.id === id);
    setCtx((c) => ({
      ...c,
      runId: id,
      origin:
        r?.kind === "forecast" ? "2025-10-31" : (r?.as_of_date ?? c.origin),
      warehouseId: "",
      itemId: "",
      supplierId: "",
      productType: "",
    }));
  }
  function navigate(id: string) {
    setPage(id);
    setNavOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  function openItem(row: Record<string, unknown>, target = "inventory") {
    setCtx((c) => ({
      ...c,
      warehouseId: String(row.warehouse_id ?? ""),
      itemId: String(row.item_id ?? ""),
    }));
    navigate(target);
  }
  const chooseInventory = compatible
    ? () => selectRun(compatible.id)
    : undefined;
  const props = { run, ctx, onChoose: chooseInventory };
  const node =
    page === "forecast" ? (
      <Forecast run={run} ctx={ctx} />
    ) : page === "inventory" ? (
      <Inventory {...props} />
    ) : page === "replenishment" ? (
      <Replenishment {...props} />
    ) : page === "alerts" ? (
      <Alerts {...props} />
    ) : page === "configuration" ? (
      <Configuration onChanged={() => setRefresh((v) => v + 1)} />
    ) : (
      <Overview
        {...props}
        runs={runs}
        onRun={selectRun}
        onCreate={() => setDialog(true)}
        onNavigate={navigate}
        onItem={openItem}
      />
    );
  const selectedTitle = PAGES.find((p) => p[0] === page)?.[2] ?? "Tổng quan";
  return (
    <div className={"shell " + (navOpen ? "nav-open" : "")}>
      {navOpen && (
        <button
          className="nav-scrim"
          aria-label="Đóng menu"
          onClick={() => setNavOpen(false)}
        />
      )}
      <aside className="sidebar">
        <a
          className="brand"
          href="#overview"
          onClick={(e) => {
            e.preventDefault();
            navigate("overview");
          }}
        >
          <span className="brand-symbol">
            <Icon name="box" size={23} />
          </span>
          <div>
            <strong>
              sigma<span>.</span>
            </strong>
            <small>Inventory workspace</small>
          </div>
        </a>
        <div className="nav-label">QUẢN LÝ KHO</div>
        <nav aria-label="Điều hướng chính">
          {PAGES.slice(0, 5).map(([id, icon, name]) => (
            <button
              key={id}
              title={name}
              className={page === id ? "selected" : ""}
              aria-current={page === id ? "page" : undefined}
              onClick={() => navigate(id)}
            >
              <Icon name={icon} />
              <span>{name}</span>
              {page === id && <i />}
            </button>
          ))}
        </nav>
        <div className="nav-label settings-label">THIẾT LẬP</div>
        <nav aria-label="Thiết lập">
          <button
            className={page === "configuration" ? "selected" : ""}
            aria-current={page === "configuration" ? "page" : undefined}
            onClick={() => navigate("configuration")}
          >
            <Icon name="settings" />
            <span>Cấu hình</span>
          </button>
        </nav>
        <div className="side-note">
          <div className="workspace-icon">
            <Icon name="box" />
          </div>
          <div>
            <strong>SIGMA Workspace</strong>
            <span>
              <i className="live-dot" /> Môi trường mô phỏng
            </span>
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-menu"
              aria-label="Mở menu"
              onClick={() => setNavOpen(true)}
            >
              <Icon name="menu" />
            </button>
            <span className="breadcrumb-root">Quản lý kho</span>
            <Icon name="chevron" size={14} />
            <strong>{selectedTitle}</strong>
          </div>
          <div className="top-status">
            {busyRun && (
              <button
                className="task-indicator"
                onClick={() => {
                  selectRun(busyRun.id);
                  navigate("overview");
                }}
              >
                <i className="spinner" />
                Đang xử lý
              </button>
            )}
            <span className="environment-pill">
              <Icon name="info" size={14} /> Dữ liệu mô phỏng
            </span>
            <button className="primary" onClick={() => setDialog(true)}>
              <Icon name="plus" size={17} />
              Tạo phương án
            </button>
          </div>
        </header>
        <div className="workspace">
          {page !== "configuration" && (
            <>
              <section
                className="context-bar"
                aria-label="Bộ lọc cùng lượt chạy"
              >
                <label className="plan-filter">
                  Phương án
                  <select
                    aria-label="Lượt chạy"
                    value={ctx.runId}
                    onChange={(e) => selectRun(e.target.value)}
                  >
                    <option value="">Chọn phương án</option>
                    {runs.map((r) => (
                      <option key={r.id} value={r.id}>
                        {label(r.kind)} · {r.as_of_date} · {r.id.slice(0, 6)}
                        {r.status === "complete" ? "" : " · " + text(r.status)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Kho / tuyến
                  <select
                    aria-label="Kho / tuyến"
                    value={ctx.warehouseId}
                    onChange={(e) =>
                      setCtx((c) => ({
                        ...c,
                        warehouseId: e.target.value,
                        itemId: "",
                      }))
                    }
                  >
                    <option value="">Tất cả kho</option>
                    {catalog.data?.items.map((w) => (
                      <option key={String(w.id)} value={String(w.id)}>
                        {String(w.destination_country)} / {String(w.carrier)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Mặt hàng
                  <select
                    aria-label="SKU"
                    disabled={!ctx.warehouseId}
                    value={ctx.itemId}
                    onChange={(e) =>
                      setCtx((c) => ({ ...c, itemId: e.target.value }))
                    }
                  >
                    <option value="">
                      {ctx.warehouseId ? "Tất cả mặt hàng" : "Chọn kho trước"}
                    </option>
                    {items.data?.items.map((i) => (
                      <option key={String(i.id)} value={String(i.id)}>
                        {String(i.sku)} · {String(i.product_type)}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Ngày làm việc · UTC
                  <input
                    aria-label="Ngày xem / origin UTC"
                    type="date"
                    value={ctx.origin}
                    onChange={(e) =>
                      setCtx((c) => ({ ...c, origin: e.target.value }))
                    }
                  />
                </label>
                <details className="extra-filters">
                  <summary>
                    <Icon name="filter" size={16} /> Bộ lọc
                  </summary>
                  <div className="filter-popover">
                    <label>
                      Loại sản phẩm
                      <select
                        aria-label="Loại sản phẩm"
                        value={ctx.productType}
                        onChange={(e) =>
                          setCtx((c) => ({
                            ...c,
                            productType: e.target.value,
                            itemId: "",
                          }))
                        }
                      >
                        <option value="">Tất cả</option>
                        <option>eSIM</option>
                        <option>physical_SIM</option>
                      </select>
                    </label>
                    <label>
                      Nhà cung cấp
                      <select
                        aria-label="Nhà cung cấp"
                        disabled={!run || !inventoryKinds.includes(run.kind)}
                        value={ctx.supplierId}
                        onChange={(e) =>
                          setCtx((c) => ({ ...c, supplierId: e.target.value }))
                        }
                      >
                        <option value="">Tất cả</option>
                        {suppliers.data?.items.map((s) => (
                          <option key={String(s.id)} value={String(s.id)}>
                            {String(s.code)}
                          </option>
                        ))}
                      </select>
                    </label>
                    <button
                      className="text-button"
                      onClick={() =>
                        setCtx((c) => ({
                          ...c,
                          warehouseId: "",
                          itemId: "",
                          supplierId: "",
                          productType: "",
                        }))
                      }
                    >
                      Xóa bộ lọc
                    </button>
                  </div>
                </details>
              </section>
              <div className="context-meta">
                {run && (
                  <>
                    <span>
                      {badge(run.status)}
                      <span className="plan-type">{label(run.kind)}</span>
                    </span>
                    <details>
                      <summary>
                        Thông tin phương án <Icon name="info" size={13} />
                      </summary>
                      <div className="context-popover">
                        <strong>Nguồn & phiên bản</strong>
                        <dl>
                          <dt>Mã phương án</dt>
                          <dd>{run.id}</dd>
                          <dt>Mốc chốt UTC</dt>
                          <dd>{run.as_of_date}</dd>
                          <dt>Quan sát đến</dt>
                          <dd>{run.observation_end}</dd>
                          <dt>Cấu hình</dt>
                          <dd>{run.config_version}</dd>
                          <dt>Giả định</dt>
                          <dd>{run.assumption_version}</dd>
                        </dl>
                        <p>
                          Snapshot lịch sử 2024–2025. Tồn và nhập là mô phỏng;
                          chưa quan sát actual sau 31/12/2025. L7 · R1 · H14.
                        </p>
                      </div>
                    </details>
                  </>
                )}
              </div>
            </>
          )}
          <State
            loading={runsResource.loading && !runsResource.data}
            error={runsResource.error}
          />
          {ctx.runId &&
          runsResource.data &&
          !run &&
          !selectedResource.loading ? (
            <div className="notice error" role="alert">
              Không tìm thấy phương án trong liên kết. Hãy chọn lại phương án;
              dữ liệu không được tự đổi sang kế hoạch khác.
            </div>
          ) : (
            <Suspense fallback={<State loading />}>{node}</Suspense>
          )}
          <footer>
            <span>SIGMA · Quản lý nhu cầu & tồn kho</span>
            <span>
              L7 · R1 · H14 <span className="footer-dot">·</span> Ngày nghiệp vụ
              UTC
            </span>
          </footer>
        </div>
      </main>
      {dialog && (
        <RunDialog
          runs={runs}
          onClose={() => setDialog(false)}
          onCreated={(id) => {
            setDialog(false);
            setCtx((c) => ({ ...c, runId: id, origin: "" }));
            setRefresh((v) => v + 1);
            navigate("overview");
          }}
        />
      )}
    </div>
  );
}
