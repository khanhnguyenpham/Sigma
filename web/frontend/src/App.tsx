import { lazy } from "react";
import { Inventory } from "./pages/Inventory";
import { Replenishment } from "./pages/Replenishment";
import { Configuration } from "./pages/Configuration";

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
    selectRun,
    setDialog,
    navigate,
    setRefresh,
  } = app;
  const props = { run, ctx, onChoose: chooseInventory, onItem: openItem };
  const node =
    page === "forecast" ? (
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
  return <AppLayout app={app}>{node}</AppLayout>;
}
