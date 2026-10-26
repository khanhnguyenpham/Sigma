import { useState } from "react";
import { api } from "../services/http";
import { type Page, type Row } from "../types/api";
import { query } from "../utils/url";
import { useResource } from "./useResource";
import { useDialogFocus } from "./useDialogFocus";

export function useConfiguration(onChanged: () => void) {
  const [tab, setTab] = useState("warehouses"),
    [page, setPage] = useState(1),
    [version, setVersion] = useState(0),
    [message, setMessage] = useState(""),
    [error, setError] = useState<Error>(),
    [busy, setBusy] = useState(false);
  const [city, setCity] = useState<Row>(),
    [policy, setPolicy] = useState<Row>(),
    [newScenario, setNewScenario] = useState(false),
    [warehouse, setWarehouse] = useState(""),
    [overrides, setOverrides] = useState<Row[]>([]),
    [receipts, setReceipts] = useState<Row[]>([]);
  useDialogFocus(!!city || !!policy || newScenario, () => {
    setCity(undefined);
    setPolicy(undefined);
    setNewScenario(false);
  });
  const data = useResource<Page>(
    `/${tab === "policies" ? "supplier-item-policies" : tab}?${query({ page, page_size: 50, refresh: undefined })}&v=${version}`,
  );
  const supplierData = useResource<Page>("/suppliers?page_size=100");
  const warehouses = useResource<Page>("/warehouses?page_size=100");
  const itemData = useResource<Page>(
    warehouse ? `/items?warehouse_id=${warehouse}&page_size=100` : null,
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
  async function save(event: React.FormEvent<HTMLFormElement>, kind: string) {
    event.preventDefault();
    if (!event.currentTarget.reportValidity()) return;
    if (busy) return;
    setBusy(true);
    setError(undefined);
    setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      let path = "",
        method = "POST",
        body: Row = {};
      if (kind === "city") {
        path = `/warehouses/${city?.id}`;
        method = "PATCH";
        body = {
          city: String(form.get("city")),
          expected_version: city?.version,
        };
      }
      if (kind === "policy") {
        path = "/supplier-item-policies";
        body = {
          item_id: Number(form.get("item_id")),
          supplier_id: Number(form.get("supplier_id")),
          effective_from: String(form.get("effective_from")),
          configured_rop_floor: Number(form.get("configured_rop_floor")),
          moq: Number(form.get("moq")),
          safety_days: Number(form.get("safety_days")),
          safety_mode: String(form.get("safety_mode")),
          safety_lookback_days: Number(form.get("safety_lookback_days")),
          safety_factor: Number(form.get("safety_factor")),
          rop_mode: String(form.get("rop_mode")),
          warning_horizon_days: Number(form.get("warning_horizon_days")),
          expected_version: policy?.version ?? 0,
        };
      }
      if (kind === "scenario") {
        path = "/scenarios";
        body = {
          name: String(form.get("name")),
          code: String(form.get("code")),
          description: String(form.get("description") ?? ""),
          settings: {
            cover_days: Number(form.get("cover_days")),
            safety_multiplier: Number(form.get("safety_multiplier")),
            policy_overrides: overrides.map((row) => {
              const active = { ...row };
              if (row.safety_mode !== "days") delete active.safety_days;
              if (row.safety_mode !== "volatility") {
                delete active.safety_lookback_days;
                delete active.safety_factor;
              }
              return active;
            }),
            receipts_initial: receipts,
            receipts_declared: true,
          },
        };
      }
      await api(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setCity(undefined);
      setPolicy(undefined);
      setNewScenario(false);
      setVersion((v) => v + 1);
      setMessage(
        "Đã lưu phiên bản mới. Phương án đang xem vẫn giữ dữ liệu và cấu hình cũ.",
      );
      onChanged();
    } catch (e) {
      setError(e as Error);
    } finally {
      setBusy(false);
    }
  }
  return {
    tab,
    setTab,
    page,
    setPage,
    message,
    error,
    setError,
    busy,
    city,
    setCity,
    policy,
    setPolicy,
    newScenario,
    setNewScenario,
    warehouse,
    setWarehouse,
    overrides,
    setOverrides,
    receipts,
    setReceipts,
    data,
    supplierData,
    warehouses,
    itemData,
    itemOptions,
    update,
    updateReceiptDate,
    save,
  };
}
export type ConfigurationState = ReturnType<typeof useConfiguration>;
