import { lazy, Suspense, useEffect, useState } from "react";
import {
  type Run,
  type Page,
  type Row,
  type Context,
  readContext,
  contextUrl,
  label,
} from "./api/client";
import { useResource, State, badge } from "./components/common";
import { RunDialog } from "./components/RunDialog";
import { Overview } from "./pages/Overview";
const Forecast = lazy(() =>
  import("./pages/Forecast").then((m) => ({ default: m.Forecast })),
);
import { Inventory } from "./pages/Inventory";
import { Replenishment } from "./pages/Replenishment";
const Alerts = lazy(() =>
  import("./pages/Alerts").then((m) => ({ default: m.Alerts })),
);
import { Configuration } from "./pages/Configuration";
import "./styles.css";
const PAGES = [
  ["overview", "◈", "Tổng quan"],
  ["forecast", "↗", "Dự báo"],
  ["inventory", "▤", "Tồn kho"],
  ["replenishment", "⇣", "Nhập hàng"],
  ["alerts", "◉", "Cảnh báo"],
  ["configuration", "⚙", "Cấu hình"],
];
export default function App() {
  const [ctx, setCtx] = useState<Context>(readContext),
    [page, setPage] = useState(location.hash.slice(1) || "overview"),
    [dialog, setDialog] = useState(false),
    [refresh, setRefresh] = useState(0);
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
  const runs = selectedResource.data && !latest.some(r=>r.id===selectedResource.data?.id)
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
      ? `/items?warehouse_id=${ctx.warehouseId}&page_size=100${run?.status === "complete" ? `&run_id=${run.id}` : ""}`
      : null,
  );
  const suppliers = useResource<Page>("/suppliers?page_size=100");
  const hasWork = runs.some(
    (r) => r.status === "queued" || r.status === "running",
  );
  useEffect(() => {
    const timer = setInterval(
      () => setRefresh((v) => v + 1),
      hasWork ? 2000 : 15000,
    );
    return () => clearInterval(timer);
  }, [hasWork]);
  useEffect(() => {
    if (ctx.runId || !runs.length) return;
    const preferred =
      runs.find(
        (r) =>
          r.status === "complete" &&
          r.kind === "stock_projection" &&
          r.as_of_date === "2025-10-31",
      ) ??
      runs.find((r) => r.status === "complete" && r.kind === "policy_replay") ??
      runs.find((r) => r.status === "complete");
    if (preferred) selectRun(preferred.id);
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
    const selected = runs.find((r) => r.id === id);
    const origin =
      selected?.kind === "forecast"
        ? "2025-10-31"
        : (selected?.as_of_date ?? ctx.origin);
    setCtx((c) => ({
      ...c,
      runId: id,
      origin,
      warehouseId: "",
      itemId: "",
      supplierId: "",
    }));
  }
  function navigate(id: string) {
    setPage(id);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  const props = { run, ctx };
  const pageNode =
    page === "forecast" ? (
      <Forecast {...props} />
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
        run={run}
        runs={runs}
        onRun={selectRun}
        onCreate={() => setDialog(true)}
      />
    );
  return (
    <div className="shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#overview"
          onClick={(e) => {
            e.preventDefault();
            navigate("overview");
          }}
        >
          <span className="brand-symbol">S</span>
          <div>
            <strong>SIGMA</strong>
            <small>DEMAND & INVENTORY</small>
          </div>
        </a>
        <div className="nav-label">ĐIỀU PHỐI</div>
        <nav>
          {PAGES.map(([id, icon, name], index) => (
            <button
              key={id}
              title={name}
              className={page === id ? "selected" : ""}
              onClick={() => navigate(id)}
              aria-current={page === id ? "page" : undefined}
            >
              <span>{icon}</span>
              {name}
              <small>{String(index + 1).padStart(2, "0")}</small>
            </button>
          ))}
        </nav>
        <div className="side-note">
          <span className="live-dot" /> MÔI TRƯỜNG LOCAL
          <p>
            Kho & nhập mô phỏng
            <br />
            L7 · R1 · H14
            <br />
            Ngày nghiệp vụ UTC
          </p>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div className="breadcrumb">
            SIGMA <span>/</span>{" "}
            {PAGES.find((p) => p[0] === page)?.[2] ?? "Tổng quan"}
          </div>
          <div className="top-status">
            {run ? (
              badge(run.status)
            ) : (
              <span className="badge">Chưa chọn lượt</span>
            )}
            <span className="source-tag">SNAPSHOT 2024–2025</span>
            <button className="small primary" onClick={() => setDialog(true)}>
              ＋ Chạy phương án
            </button>
          </div>
        </header>
        <div className="workspace">
          <section className="context-bar" aria-label="Bộ lọc cùng lượt chạy">
            <label>
              Lượt chạy
              <select
                aria-label="Lượt chạy"
                value={ctx.runId}
                onChange={(e) => selectRun(e.target.value)}
              >
                <option value="">Chọn lượt đã có</option>
                {runs.map((r) => (
                  <option key={r.id} value={r.id}>
                    {label(r.kind)} · {r.as_of_date} · {r.id.slice(0, 8)} ·{" "}
                    {r.status}
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
              SKU
              <select
                aria-label="SKU"
                disabled={!ctx.warehouseId}
                value={ctx.itemId}
                onChange={(e) =>
                  setCtx((c) => ({ ...c, itemId: e.target.value }))
                }
              >
                <option value="">Tất cả mặt hàng</option>
                {items.data?.items.map((i) => (
                  <option key={String(i.id)} value={String(i.id)}>
                    {String(i.sku)} · {String(i.product_type)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Ngày xem / origin UTC
              <input
                aria-label="Ngày xem / origin UTC"
                type="date"
                value={ctx.origin}
                onChange={(e) =>
                  setCtx((c) => ({ ...c, origin: e.target.value }))
                }
              />
            </label>
            <button
              className="clear"
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
              Xóa lọc
            </button>
          </section>
          <div className="context-meta">
            {run ? (
              <>
                <span>
                  {label(run.kind)} · #{run.id.slice(0, 8)}
                </span>
                <span>
                  Mốc chốt {run.as_of_date} · Quan sát đến {run.observation_end}
                </span>
                <span>
                  {run.kind === "forecast" || run.kind === "source_import"
                    ? "Nguồn snapshot hồi cứu"
                    : "TỒN / NHẬP MÔ PHỎNG"}
                </span>
              </>
            ) : (
              <span>Chọn một lượt chạy để giữ nhất quán số liệu.</span>
            )}
            <details>
              <summary>Lọc thêm</summary>
              <label>
                Loại sản phẩm
                <select
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
                Supplier
                <select
                  disabled={
                    run?.kind === "forecast" || run?.kind === "source_import"
                  }
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
            </details>
          </div>
          <State
            loading={runsResource.loading && !runsResource.data}
            error={runsResource.error}
          />
          {ctx.runId &&
          runsResource.data &&
          !run &&
          !selectedResource.loading ? (
            <div className="notice error" role="alert">
              Lượt chạy trong URL không tồn tại. Chọn lại từ danh sách; ứng dụng
              không tự thay sang lượt khác.
            </div>
          ) : (
            <Suspense fallback={<State loading />}>{pageNode}</Suspense>
          )}
          <footer>
            <span>SIGMA · Nhu cầu & tồn kho</span>
            <span>
              Actual · Dự báo · Phân bổ · Giả định · Mô phỏng được tách rõ
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
            setPage("overview");
          }}
        />
      )}
    </div>
  );
}
