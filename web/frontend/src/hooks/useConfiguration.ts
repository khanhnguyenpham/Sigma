import { useState } from "react";
import { api } from "../services/http";
import { type Page, type Row } from "../types/api";
import { query } from "../utils/url";
import { useResource } from "./useResource";
import { useDialogFocus } from "./useDialogFocus";

export function useConfiguration(onChanged: () => void) {
  const [page, setPage] = useState(1),
    [version, setVersion] = useState(0),
    [message, setMessage] = useState(""),
    [error, setError] = useState<Error>(),
    [busy, setBusy] = useState(false);
  const [newScenario, setNewScenario] = useState(false),
    [warehouse, setWarehouse] = useState(""),
    [overrides, setOverrides] = useState<Row[]>([]),
    [receipts, setReceipts] = useState<Row[]>([]);
  useDialogFocus(newScenario, () => {
    setNewScenario(false);
  });
  const data = useResource<Page>(
    `/scenarios?${query({ page, page_size: 50 })}&v=${version}`,
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
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!event.currentTarget.reportValidity()) return;
    if (busy) return;
    setBusy(true);
    setError(undefined);
    setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      const body: Row = {
          name: String(form.get("name")),
          code: String(form.get("code")),
          description: String(form.get("description") ?? ""),
          settings: {
            cover_days: Number(form.get("cover_days")),
            safety_multiplier: Number(form.get("safety_multiplier")),
            policy_overrides: overrides,
            receipts_initial: receipts,
            receipts_declared: true,
          },
        };
      await api("/scenarios", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setNewScenario(false);
      setVersion((v) => v + 1);
      setMessage(
        "Đã lưu thiết lập tính toán.",
      );
      onChanged();
    } catch (e) {
      setError(e as Error);
    } finally {
      setBusy(false);
    }
  }
  return {
    page,
    setPage,
    message,
    error,
    setError,
    busy,
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
