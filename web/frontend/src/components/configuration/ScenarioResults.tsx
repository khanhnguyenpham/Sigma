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
import { ForecastComparison } from "../forecast/ForecastComparison";
import { EarlyWarningResult } from "../alerts/EarlyWarningResult";
import { SupplyImpactTab } from "./SupplyImpactResult";

export function ScenarioResults({ app, run }: { app: AppContextState; run: Run }) {
  const [tab, setTab] = useState("summary");
  const inventory = inventoryKinds.includes(run.kind);
  const replay = run.scenario_id == null ? undefined : app.runs.find(row => row.kind === "alert_replay" &&
    row.status === "complete" && row.scenario_id === run.scenario_id &&
    row.forecast_run_id === run.forecast_run_id && row.source_import_run_id === run.source_import_run_id);
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
        {[["summary", "Tóm tắt"], ["comparison", "So sánh dự báo / thực tế"], ["inventory", "Tồn kho"], ["replenishment", "Nhập hàng"], ["alerts", "Cảnh báo"], ["supply", "Ngừng cung cấp"]].map(([key, name]) =>
          <button key={key} type="button" className={tab === key ? "primary" : "secondary"} aria-pressed={tab === key} onClick={() => setTab(key)}>{name}</button>)}
      </nav>
      {tab === "summary" && <>
        <EarlyWarningResult run={run} replay={replay} onOpenReplay={() => { if (replay) app.openScenarios(replay.id); }} />
        <Overview {...props} embedded runs={[run]} onRun={(id) => app.openScenarios(id)} onCreate={() => app.openScenarios()} onNavigate={app.navigate} />
      </>}
      {tab === "comparison" && <ForecastComparison key={run.id} run={run} ctx={app.ctx} />}
      {tab === "supply" && <SupplyImpactTab {...props} />}
      {tab === "inventory" && <Inventory {...props} catalog={app.catalog} itemOptions={app.items.data?.items ?? []}
        supplierOptions={app.suppliers.data?.items ?? []} onWarehouse={warehouse}
        onFilterChange={(patch) => app.setCtx((current) => ({ ...current, ...patch }))} onNavigate={app.navigate} />}
      {tab === "replenishment" && <Replenishment {...props} />}
      {tab === "alerts" && <Alerts {...props} />}
    </> : <Forecast run={run} ctx={app.ctx} />}
  </div>;
}
