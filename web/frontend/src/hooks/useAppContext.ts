import { inventoryKinds } from "../config/navigation";
import { readPurchasingView } from "../utils/url";
import { useEffect, useState } from "react";
import { type Run, type Page } from "../types/api";
import { type Context } from "../types/context";
import { readContext, contextUrl } from "../utils/url";
import { useResource } from "./useResource";
import { type PurchasingView } from "../types/context";

export function useAppContext() {
  const [ctx, setCtx] = useState<Context>(readContext);
  const [page, setPage] = useState(location.hash.slice(1) || "overview");
  const [help, setHelp] = useState(false);
  const [dialog, setDialog] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const [purchasingView, setPurchasingView] =
    useState<PurchasingView>(readPurchasingView);
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
    history.replaceState(
      null,
      "",
      "?" +
        contextUrl(ctx) +
        (page === "replenishment" ? "&view=" + purchasingView : "") +
        "#" +
        page,
    );
  }, [ctx, page, purchasingView]);
  useEffect(() => {
    const pop = () => {
      setCtx(readContext());
      setPurchasingView(readPurchasingView());
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
      origin:
        r?.kind === "forecast" ? "2025-10-31" : (r?.as_of_date ?? c.origin),
      warehouseId: "",
      itemId: "",
      supplierId: "",
      productType: "",
    }));
  }
  function navigate(id: string, view: PurchasingView = "recommendations") {
    if (id !== page)
      history.pushState(
        null,
        "",
        "?" +
          contextUrl(ctx) +
          (id === "replenishment" ? "&view=" + view : "") +
          "#" +
          id,
      );
    if (id === "replenishment") setPurchasingView(view);
    setPage(id);
    setNavOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  function openItem(
    row: Record<string, unknown>,
    target = "inventory",
    view: PurchasingView = "recommendations",
  ) {
    setCtx((c) => ({
      ...c,
      warehouseId: String(row.warehouse_id ?? ""),
      itemId: String(row.item_id ?? ""),
    }));
    navigate(target, view);
  }
  function selectWarehouse(id: string) {
    const next = { ...ctx, warehouseId: id, itemId: "", supplierId: "", productType: "" };
    history.pushState(null, "", "?" + contextUrl(next) + "#" + page);
    setCtx(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  const chooseInventory = compatible
    ? () => selectRun(compatible.id)
    : undefined;
  return {
    ctx,
    setCtx,
    page,
    setPage,
    help,
    setHelp,
    dialog,
    setDialog,
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
    openItem,
    selectWarehouse,
    chooseInventory,
  };
}
export type AppContextState = ReturnType<typeof useAppContext>;
