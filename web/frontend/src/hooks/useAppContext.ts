import { inventoryKinds } from "../config/navigation";
import { readPurchasingView } from "../utils/url";
import { useEffect, useRef, useState } from "react";
import { type Run, type Page } from "../types/api";
import { type Context } from "../types/context";
import { readContext, contextUrl, navigationUrl, readPage } from "../utils/url";
import { useResource } from "./useResource";
import { type PurchasingView } from "../types/context";
import { isReceivingRun } from "../utils/warehouse";
import { api, apiAllPages } from "../services/http";

export function useAppContext() {
  const [ctx, setCtx] = useState<Context>(readContext);
  const datedRun = useRef("");
  const [page, setPage] = useState(readPage);
  const [help, setHelp] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const [purchasingView, setPurchasingView] =
    useState<PurchasingView>(readPurchasingView);
  const [refresh, setRefresh] = useState(0);
  const currentUrl = useRef("");
  currentUrl.current = navigationUrl(ctx, page, purchasingView);
  const [scenarioRevision, setScenarioRevision] = useState(0);
  const runsResource = useResource<Page<Run>>(
    `/runs?page_size=100&refresh=${refresh}`,
    true,
  );
  const latest = runsResource.data?.items ?? [];
  const [runRevision, setRunRevision] = useState(0);
  const selectedResource = useResource<Run>(
    ctx.runId && (page === "scenarios" || !latest.some((r) => r.id === ctx.runId))
      ? `/runs/${ctx.runId}`
      : null,
    true, runRevision,
  );
  useEffect(() => {
    if (!selectedResource.data || !["queued", "running"].includes(selectedResource.data.status)) return;
    const timer = setInterval(() => setRunRevision((value) => value + 1), 2000);
    return () => clearInterval(timer);
  }, [selectedResource.data?.id, selectedResource.data?.status]);
  const runs =
    selectedResource.data?.id === ctx.runId &&
    !latest.some((r) => r.id === selectedResource.data?.id)
      ? [...latest, selectedResource.data]
      : latest;
  const run = selectedResource.data?.id === ctx.runId ? selectedResource.data : runs.find((r) => r.id === ctx.runId);
  const snapshotDate = run?.kind === "stock_projection" &&
    ["overview", "inventory", "replenishment", "alerts", "forecast", "scenarios"].includes(page)
    ? run.as_of_date : undefined;
  const viewContext = snapshotDate && ctx.origin !== snapshotDate ? { ...ctx, origin: snapshotDate } : ctx;
  useEffect(() => {
    if (snapshotDate && ctx.origin !== snapshotDate)
      setCtx((current) => ({ ...current, origin: snapshotDate }));
  }, [snapshotDate, ctx.origin]);
  const catalog = useResource<Page>(
    run?.status === "complete"
      ? `/warehouses?run_id=${run.id}&page_size=100`
      : "/warehouses?page_size=100",
  );
  const items = useResource<Page>(
    ctx.warehouseId
      ? `/items?${ctx.warehouseScope === "receiving" && run?.status === "complete" ? "receiving_warehouse_id" : "warehouse_id"}=${ctx.warehouseId}&page_size=100${run?.status === "complete" ? "&run_id=" + run.id : ""}`
      : null,
    false, 0, ctx.warehouseScope === "receiving" ? apiAllPages : api,
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
    if (!run || ["products", "product", "product-supply", "configuration"].includes(page) || page.startsWith("provider-")) return;
    const scope = isReceivingRun(run) ? "receiving" : undefined;
    setCtx((current) => current.warehouseScope === scope ? current : { ...current, warehouseScope: scope });
  }, [run?.id, run?.receiving_warehouse_profile, page, ctx.warehouseScope]);
  useEffect(() => {
    const timer = setInterval(
      () => setRefresh((v) => v + 1),
      hasWork ? 2000 : 15000,
    );
    return () => clearInterval(timer);
  }, [hasWork]);
  useEffect(() => {
    if (page !== "scenarios" && !ctx.runId && runs.length) {
      const preferred = compatible ?? runs.find((r) => r.status === "complete");
      if (preferred) {
        if (ctx.itemId && (["product", "product-supply"].includes(page) || page.startsWith("provider-")))
          setCtx((current) => ({ ...current, runId: preferred.id }));
        else selectRun(preferred.id);
      }
    }
  }, [runsResource.data, page]);
  useEffect(() => {
    history.replaceState(
      history.state,
      "",
      navigationUrl(ctx,page,purchasingView),
    );
  }, [ctx, page, purchasingView]);
  useEffect(() => {
    const pop = () => {
      const next = navigationUrl(readContext(), readPage(), readPurchasingView());
      if (next === currentUrl.current) return;
      if(!window.dispatchEvent(new CustomEvent("sigma:before-navigate",{cancelable:true,detail:{pop:true}})))return;
      currentUrl.current = next;
      setCtx(readContext());
      setPurchasingView(readPurchasingView());
      setPage(readPage());
    };
    window.addEventListener("popstate", pop);
    window.addEventListener("hashchange", pop);
    return () => { window.removeEventListener("popstate", pop); window.removeEventListener("hashchange", pop); };
  }, [page]);
  useEffect(() => {
    if (
      !["product", "product-supply", "scenarios"].includes(page) && !page.startsWith("provider-") && ctx.itemId &&
      items.data &&
      !items.data.items.some((i) => String(i.id) === ctx.itemId)
    )
      setCtx((c) => ({ ...c, itemId: "" }));
  }, [items.data, page]);
  useEffect(() => {
    // Default once per selected run, preserving an explicit clear across retries.
    if (!run || datedRun.current === run.id) return;
    datedRun.current = run.id;
    if (!ctx.origin)
      setCtx((c) => ({
        ...c,
        origin: run.kind === "forecast" ? "2025-10-31" : run.as_of_date,
      }));
  }, [run?.id]);
  useEffect(() => {
    if (!navOpen) return;
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setNavOpen(false);
        document
          .querySelector<HTMLButtonElement>('[aria-label="Mở menu"]')
          ?.focus();
      }
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [navOpen]);
  function selectRun(id: string) {
    const r = runs.find((r) => r.id === id);
    setCtx((c) => ({
      ...c,
      runId: id,
      scenarioId: r?.scenario_id ? String(r.scenario_id) : undefined,
      warehouseScope: isReceivingRun(r) ? "receiving" : undefined,
      origin:
        r?.kind === "forecast" ? "2025-10-31" : (r?.as_of_date ?? c.origin),
      warehouseId: "",
      itemId: "",
      supplierId: "",
      carrier: "",
      productType: "",
      internalStatus:"",providerStatus:"",replenishmentAllowed:"",salesAllowed:"",windowOrigin:"",
    }));
  }
  function navigate(id: string, view: PurchasingView = "recommendations") {
    if(!window.dispatchEvent(new Event("sigma:before-navigate",{cancelable:true})))return false;
    if (id === "configuration") id = "scenarios";
    if (id !== page)
      history.pushState(
        null,
        "",
        navigationUrl(ctx,id,view),
      );
    if (id === "replenishment") setPurchasingView(view);
    setPage(id);
    setNavOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
    return true;
  }
  function scenarioContext(next: Context, push = true) {
    if (push) history.pushState(history.state, "", navigationUrl(next, "scenarios", purchasingView));
    setCtx(next); setPage("scenarios"); setNavOpen(false);
  }
  function openScenarios(id = "", scenarioId?: string) {
    if (!window.dispatchEvent(new Event("sigma:before-navigate", { cancelable: true }))) return false;
    const selected = runs.find((row) => row.id === id);
    setScenarioRevision((value) => value + 1);
    scenarioContext({ ...ctx, runId: id, scenarioId: scenarioId ?? (id ? selected?.scenario_id ? String(selected.scenario_id) : undefined : ctx.scenarioId),
      ...(id !== ctx.runId ? { origin: selected?.as_of_date ?? "", warehouseId: "", itemId: "", supplierId: "", productType: "",
        carrier: "", internalStatus: "", providerStatus: "", replenishmentAllowed: "", salesAllowed: "", windowOrigin: "" } : {}) });
    return true;
  }
  function chooseScenario(id: string) {
    if (!window.dispatchEvent(new Event("sigma:before-navigate", { cancelable: true }))) return false;
    setScenarioRevision((value) => value + 1);
    scenarioContext({ ...ctx, scenarioId: id, runId: "", origin: "", warehouseId: "", itemId: "", supplierId: "", productType: "",
      carrier: "", internalStatus: "", providerStatus: "", replenishmentAllowed: "", salesAllowed: "", windowOrigin: "" });
    return true;
  }
  function scenarioSaved(id: string) {
    scenarioContext({ ...ctx, scenarioId: id, runId: "", origin: "", warehouseId: "", itemId: "", supplierId: "", productType: "",
      carrier: "", internalStatus: "", providerStatus: "", replenishmentAllowed: "", salesAllowed: "", windowOrigin: "" });
    setRefresh((value) => value + 1);
  }
  function scenarioRunCreated(id: string, scenarioId = ctx.scenarioId) {
    scenarioContext({ ...ctx, runId: id, scenarioId, origin: "", warehouseId: "", itemId: "", supplierId: "", productType: "",
      carrier: "", internalStatus: "", providerStatus: "", replenishmentAllowed: "", salesAllowed: "", windowOrigin: "" });
    setRunRevision((value) => value + 1); setRefresh((value) => value + 1);
  }
  function openItem(
    row: Record<string, unknown>,
    target = "inventory",
    view: PurchasingView = "recommendations",
  ) {
    if (!navigate(target, view)) return;
    const management = target === "product" || target === "product-supply";
    setCtx((c) => ({
      ...c,
      warehouseId: String(management ? row.source_warehouse_id ?? row.warehouse_id ?? "" : row.receiving_warehouse_id ?? row.warehouse_id ?? ""),
      warehouseScope: !management && isReceivingRun(run) ? "receiving" : undefined,
      itemId: String(row.item_id ?? ""),
    }));
  }
  function selectWarehouse(id: string) {
    if (!window.dispatchEvent(new Event("sigma:before-navigate", { cancelable: true }))) return;
    const next: Context = { ...ctx, warehouseId: id, warehouseScope: isReceivingRun(run) ? "receiving" : undefined,
      itemId: "", supplierId: "", productType: "" };
    history.pushState(null, "", "?" + contextUrl(next) + "#inventory");
    setCtx(next);
    setPage("inventory");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  const chooseInventory = compatible
    ? () => selectRun(compatible.id)
    : undefined;
  return {
    ctx: viewContext,
    setCtx,
    page,
    setPage,
    help,
    setHelp,
    navOpen,
    setNavOpen,
    purchasingView,
    setPurchasingView,
    refresh,
    setRefresh,
    runsResource,
    selectedResource,
    runs,
    run,
    catalog,
    items,
    suppliers,
    hasWork,
    compatible,
    busyRun,
    selectRun,
    navigate,
    openScenarios,
    chooseScenario,
    scenarioSaved,
    scenarioRunCreated,
    scenarioRevision,
    openItem,
    selectWarehouse,
    chooseInventory,
  };
}
export type AppContextState = ReturnType<typeof useAppContext>;
