import { lazy } from "react";
import { Inventory } from "./pages/Inventory";
import { Replenishment } from "./pages/Replenishment";
import { Products, ProductDetail } from "./pages/Products";

import { useAppContext } from "./hooks/useAppContext";

import { AppLayout } from "./layouts/AppLayout";

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
  const node =
    page === "products" ? (
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
