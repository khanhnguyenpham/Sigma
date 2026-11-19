import { lazy } from "react";
import { Inventory } from "./pages/Inventory";
import { Replenishment } from "./pages/Replenishment";
import { Products, ProductDetail } from "./pages/Products";

import { useAppContext } from "./hooks/useAppContext";

import { AppLayout } from "./layouts/AppLayout";
import { navigationUrl } from "./utils/url";
import { OPS_TAB } from "./config/navigation";
import type { Context } from "./types/context";

const Overview = lazy(() =>
  import("./pages/Overview").then((m) => ({ default: m.Overview })),
);
const Forecast = lazy(() =>
  import("./pages/Forecast").then((m) => ({ default: m.Forecast })),
);
const Alerts = lazy(() =>
  import("./pages/Alerts").then((m) => ({ default: m.Alerts })),
);
const Scenarios = lazy(() => import("./pages/Scenarios").then((module) => ({ default: module.Scenarios })));
const Operations = lazy(() => import("./pages/Operations").then((module) => ({ default: module.Operations })));
const Dashboard = lazy(() => import("./pages/Dashboard").then((module) => ({ default: module.Dashboard })));
const DealersPage = lazy(() => import("./pages/Dealers").then((module) => ({ default: module.DealersPage })));
const DealerRequestsPage = lazy(() => import("./pages/Dealers").then((module) => ({ default: module.DealerRequestsPage })));
export default function App() {
  const app = useAppContext();
  const {
    run,
    ctx,
    chooseInventory,
    openItem,
    page,
    purchasingView,
    setPurchasingView,
    runs,
    navigate,
  } = app;
  const props = { run, ctx, onChoose: chooseInventory, onItem: openItem };
  // Operations only asks to open or close an order or a supplier; every other page change goes through the sidebar.
  function opsContext(patch: Partial<Context>) {
    if (!window.dispatchEvent(new Event("sigma:before-navigate", { cancelable: true }))) return;
    const target = patch.opsTab === "orders" || patch.opsTab === "suppliers" || patch.opsTab === "stock" ? patch.opsTab : page;
    const next = { ...ctx, opsOrderId: patch.opsOrderId, opsSupplierId: patch.opsSupplierId, opsWarehouseId: patch.opsWarehouseId };
    history.pushState(null, "", navigationUrl(next, target, purchasingView));
    app.setCtx(next);
    if (target !== page) app.setPage(target);
  }
  function openOrder(id: string) { opsContext({ opsTab: "orders", opsOrderId: id }); }
  const node =
    page === "dashboard" ? <Dashboard onNavigate={navigate} onOpenOrder={openOrder} />
    : page === "dealers" ? <DealersPage />
    : page === "dealer-requests" ? <DealerRequestsPage />
    : OPS_TAB[page] ? <Operations key={page} ctx={{ ...ctx, opsTab: OPS_TAB[page] }} onContext={opsContext} />
    : page === "products" ? (
      <Products ctx={ctx.warehouseScope === "receiving" ? { ...ctx, warehouseId: "" } : ctx}
        onContext={(patch) => app.setCtx((c) => ({ ...c, ...patch, warehouseScope: undefined }))} onOpen={(row) => openItem(row, "product")} />
    ) : page === "product" ? (
      <ProductDetail run={run} ctx={ctx} onDate={(origin) => app.setCtx((c) => ({ ...c, origin }))} onNavigate={navigate} onItem={openItem}
        onWarehouse={(row) => app.selectWarehouse(String(row.warehouse_id))} />
    ) : page === "forecast" ? (
      <Forecast run={run} ctx={ctx} />
    ) : page === "inventory" ? (
      <Inventory {...props}
        catalog={app.catalog} itemOptions={app.items.data?.items ?? []}
        supplierOptions={app.suppliers.data?.items ?? []}
        onWarehouse={app.selectWarehouse}
        onFilterChange={(patch) => app.setCtx((c) => ({ ...c, ...patch }))}
        onNavigate={navigate} />
    ) : page === "replenishment" ? (
      <Replenishment
        {...props}
        view={purchasingView}
        onViewChange={setPurchasingView}
      />
    ) : page === "alerts" ? (
      <Alerts {...props} />
    ) : page === "scenarios" ? (
      <Scenarios app={app} />
    ) : (
      <Overview
        {...props}
        runs={runs}
        onRun={(id) => app.openScenarios(id)}
        onCreate={() => app.openScenarios()}
        onNavigate={navigate}
        onItem={openItem}
      />
    );
  return <AppLayout app={app}>{node}</AppLayout>;
}
