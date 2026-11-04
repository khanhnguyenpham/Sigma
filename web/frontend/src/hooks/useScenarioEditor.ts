import { useEffect, useRef, useState } from "react";
import { api, apiAllPages, ApiError } from "../services/http";
import { type Page, type Row } from "../types/api";
import { useResource } from "./useResource";

export function useScenarioEditor(scenario: Row | undefined, onSaved: (row: Row) => void) {
  const [base] = useState(() => {
    const settings = (scenario?.settings ?? {}) as Row;
    return { values: { name: scenario?.name ?? "", code: scenario?.code ?? "",
        description: scenario?.description ?? "", cover_days: String(settings.cover_days ?? 7),
        safety_multiplier: String(settings.safety_multiplier ?? 1) },
      overrides: (settings.policy_overrides ?? []) as Row[], receipts: (settings.receipts_initial ?? []) as Row[] };
  });
  const [values, setValues] = useState<Row>(base.values);
  const [error, setError] = useState<Error>(),
    [busy, setBusy] = useState(false);
  const [warehouse, setWarehouse] = useState(""),
    [overrides, setOverrides] = useState<Row[]>(base.overrides),
    [receipts, setReceipts] = useState<Row[]>(base.receipts);
  const [uncertain, setUncertain] = useState(false);
  const sending = useRef(false), pending = useRef<AbortController | undefined>(undefined);
  const [savedKey, setSavedKey] = useState(JSON.stringify(base));
  const dirty = JSON.stringify({ values, overrides, receipts }) !== savedKey;
  useEffect(() => () => pending.current?.abort(), []);
  const warehouses = useResource<Page>("/warehouses?page_size=100", false, 0, apiAllPages);
  const itemData = useResource<Page>(
    warehouse ? `/items?warehouse_id=${warehouse}&page_size=100` : null, false, 0, apiAllPages,
  );
  const itemOptions = itemData.data?.items ?? [];
  const update = (
    _rows: Row[],
    setter: React.Dispatch<React.SetStateAction<Row[]>>,
    index: number,
    key: string,
    value: unknown,
  ) =>
    setter((previous) =>
      previous.map((r, i) => (i === index ? { ...r, [key]: value } : r)),
    );
  function updateReceiptDate(index: number, ordered: string) {
    const date = new Date(ordered + "T00:00:00Z");
    date.setUTCDate(date.getUTCDate() + 7);
    const eta = Number.isNaN(date.valueOf())
      ? ""
      : date.toISOString().slice(0, 10);
    setReceipts((previous) =>
      previous.map((r, i) =>
        i === index ? { ...r, ordered_on: ordered, eta } : r,
      ),
    );
  }
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!event.currentTarget.reportValidity()) return;
    if (sending.current || uncertain) return;
    const controller = new AbortController(); pending.current = controller;
    sending.current = true;
    setBusy(true);
    setError(undefined);
    try {
      const body: Row = {
          name: String(values.name),
          code: String(values.code),
          description: String(values.description ?? ""),
          ...(scenario ? { base_scenario_id: Number(scenario.id) } : {}),
          settings: {
            cover_days: Number(values.cover_days),
            safety_multiplier: Number(values.safety_multiplier),
            policy_overrides: overrides,
            receipts_initial: receipts,
            receipts_declared: true,
          },
        };
      const saved = await api<Row>("/scenarios", {
        method: "POST",
        signal: controller.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (controller.signal.aborted) return;
      setSavedKey(JSON.stringify({ values, overrides, receipts }));
      onSaved(saved);
    } catch (e) {
      if (!controller.signal.aborted) {
        setError(e as Error);
        setUncertain(!(e instanceof ApiError) || e.code === "request_timeout" || e.status >= 500);
      }
    } finally {
      sending.current = false;
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return {
    error,
    setError,
    busy,
    warehouse,
    setWarehouse,
    overrides,
    setOverrides,
    receipts,
    setReceipts,
    warehouses,
    itemData,
    itemOptions,
    update,
    updateReceiptDate,
    save,
    values,
    setValues,
    dirty,
    uncertain,
  };
}
export type ScenarioEditorState = ReturnType<typeof useScenarioEditor>;
