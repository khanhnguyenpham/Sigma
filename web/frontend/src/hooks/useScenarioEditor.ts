import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../services/http";
import { type Row } from "../types/api";
export type ScenarioSupply = Record<"internal_stops" | "provider_stops", Row[]>;
export type ScenarioItemKind = "override" | "receipt" | keyof ScenarioSupply;

export function useScenarioEditor(scenario: Row | undefined, onSaved: (row: Row) => void) {
  const [base] = useState(() => {
    const settings = (scenario?.settings ?? {}) as Row;
    return { values: { name: scenario?.name ?? "", code: scenario?.code ?? "",
        description: scenario?.description ?? "", cover_days: String(settings.cover_days ?? 7),
        safety_multiplier: String(settings.safety_multiplier ?? 1) },
      overrides: (settings.policy_overrides ?? []) as Row[], receipts: (settings.receipts_initial ?? []) as Row[],
      schedule: { internal_stops: ((settings.supply_schedule as Row)?.internal_stops ?? []) as Row[],
        provider_stops: ((settings.supply_schedule as Row)?.provider_stops ?? []) as Row[] } };
  });
  const [values, setValues] = useState<Row>(base.values);
  const [error, setError] = useState<Error>(),
    [busy, setBusy] = useState(false);
  const [overrides, setOverrides] = useState<Row[]>(base.overrides),
    [receipts, setReceipts] = useState<Row[]>(base.receipts);
  const [schedule, setSchedule] = useState<ScenarioSupply>(base.schedule);
  const [uncertain, setUncertain] = useState(false);
  const sending = useRef(false), pending = useRef<AbortController | undefined>(undefined);
  const [savedKey, setSavedKey] = useState(JSON.stringify(base));
  const dirty = JSON.stringify({ values, overrides, receipts, schedule }) !== savedKey;
  useEffect(() => () => pending.current?.abort(), []);
  const [picker, setPicker] = useState<{kind: ScenarioItemKind; index?: number}>();
  const [pickedItems, setPickedItems] = useState<Record<number, Row>>({});
  function chooseItem(kind: ScenarioItemKind, index?: number) { setPicker({kind,index}); }
  function itemChosen(item: Row) {
    if (!picker) return;
    const id=Number(item.id), {kind,index}=picker;
    setPickedItems(previous=>({...previous,[id]:item}));
    const replace = (rows: Row[], fresh: Row) => index == null ? [...rows,fresh] : rows.map((row,i)=>i===index ? {...row,item_id:id} : row);
    if (kind==='override') setOverrides(previous=>replace(previous,{item_id:id}));
    else if (kind==='receipt') setReceipts(previous=>replace(previous,{item_id:id,ordered_on:'2025-09-30',eta:'2025-10-07',ordered_qty:10,lot_key:crypto.randomUUID()}));
    else setSchedule(previous=>({...previous,[kind]:replace(previous[kind],{item_id:id,known_on:'',effective_on:'',reason:''})}));
    setPicker(undefined);
  }
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
            supply_schedule: schedule,
          },
        };
      const saved = await api<Row>("/scenarios", {
        method: "POST",
        signal: controller.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (controller.signal.aborted) return;
      setSavedKey(JSON.stringify({ values, overrides, receipts, schedule }));
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
    overrides,
    setOverrides,
    receipts,
    setReceipts,
    schedule,
    setSchedule,
    picker,
    setPicker,
    pickedItems,
    chooseItem,
    itemChosen,
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
