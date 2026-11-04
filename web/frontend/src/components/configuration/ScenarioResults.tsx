import { useState } from "react";
import type { AppContextState } from "../../hooks/useAppContext";
import type { Run } from "../../types/api";
import { ContextFilters } from "../../layouts/ContextFilters";
import { Overview } from "../../pages/Overview";
import { Inventory } from "../../pages/Inventory";
import { Replenishment } from "../../pages/Replenishment";
import { Alerts } from "../../pages/Alerts";
import { Forecast } from "../../pages/Forecast";
import { Table } from "../ui/Table";
import { inventoryKinds } from "../../config/navigation";
import { isReceivingRun } from "../../utils/warehouse";

export function ScenarioResults({ app, run }: { app: AppContextState; run: Run }) {
  const [tab, setTab] = useState("summary");
  const inventory = inventoryKinds.includes(run.kind);
  if (run.kind === "source_import") {
    const fields: Record<string, string> = { raw_rows: "Dòng nguồn", daily_rows: "Dòng dữ liệu ngày", sales_quantity: "Lượng bán", items: "Mặt hàng", routes: "Tuyến" };
    return <Table rows={Object.entries(fields).filter(([key]) => run.result_summary[key] != null)
      .map(([key, name]) => ({ id: key, name, value: run.result_summary[key] }))}
      columns={[{ key: "name", label: "Chỉ tiêu nhập nguồn" }, { key: "value", label: "Kết quả" }]} />;
  }
  const props = { run, ctx: app.ctx, onItem: app.openItem };
  function warehouse(id: string) {
    app.setCtx((current) => ({ ...current, warehouseId: id, warehouseScope: isReceivingRun(run) ? "receiving" : undefined,
      itemId: "", supplierId: "", productType: "" }));
  }
  return <div className="scenario-results">
    <ContextFilters app={app} hideRunSelector />
    {inventory ? <>
      <nav className="scenario-result-tabs" aria-label="Kết quả của lượt chạy">
        {[["summary", "Tóm tắt"], ["inventory", "Tồn kho"], ["replenishment", "Nhập hàng"], ["alerts", "Cảnh báo"], ["forecast", "Dự kiến bán"]].map(([key, name]) =>
          <button key={key} type="button" className={tab === key ? "primary" : "secondary"} aria-pressed={tab === key} onClick={() => setTab(key)}>{name}</button>)}
      </nav>
      {tab === "summary" && <Overview {...props} embedded runs={[run]} onRun={(id) => app.openScenarios(id)} onCreate={() => app.openScenarios()} onNavigate={app.navigate} />}
      {tab === "inventory" && <Inventory {...props} catalog={app.catalog} itemOptions={app.items.data?.items ?? []}
        supplierOptions={app.suppliers.data?.items ?? []} onWarehouse={warehouse}
        onFilterChange={(patch) => app.setCtx((current) => ({ ...current, ...patch }))} onNavigate={app.navigate} />}
      {tab === "replenishment" && <Replenishment {...props} />}
      {tab === "alerts" && <Alerts {...props} />}
      {tab === "forecast" && <Forecast run={run} ctx={app.ctx} />}
    </> : <Forecast run={run} ctx={app.ctx} />}
  </div>;
}
