import { useEffect, useRef, useState } from "react";
import { api } from "../../services/http";
import type { Run, Page, Row } from "../../types/api";
import { label, errorLabel } from "../../utils/labels";
import { useResource } from "../../hooks/useResource";
import { inventoryKinds } from "../../config/navigation";
import { State } from "../ui/State";
import { TRADE_PROFILE } from "../../utils/trade";

export function RunForm({ runs, onCreated, scenario, blocked = false, loading = false, loadError,
  initialRun, onKindChange, onBusyChange }: {
  runs: Run[]; onCreated: (id: string, scenarioId?: string) => void; scenario?: Row;
  blocked?: boolean; loading?: boolean; loadError?: Error; initialRun?: Run;
  onKindChange?: (kind: string) => void; onBusyChange?: (busy: boolean) => void;
}) {
  const [kind, setKind] = useState(initialRun && inventoryKinds.includes(initialRun.kind) ? initialRun.kind : "stock_projection");
  useEffect(() => { onKindChange?.(kind); }, [kind, onKindChange]);
  const [busy, setBusy] = useState(false), [error, setError] = useState<Error>();
  const sending = useRef(false), retry = useRef<{ body: string; key: string } | undefined>(undefined);
  const pending = useRef<AbortController | undefined>(undefined);
  useEffect(() => () => pending.current?.abort(), []);
  const [forecastId, setForecastId] = useState(initialRun?.forecast_run_id ?? "");
  const forecasts = runs.filter((run) => run.kind === "forecast" && run.status === "complete");
  const forecast = forecastId ? forecasts.find((run) => run.id === forecastId)
    : forecasts.find((run) => Number(run.result_summary.origins) > 1) ?? forecasts[0];
  const availableDates = Array.isArray(forecast?.result_summary.stock_projection_origins)
    ? forecast.result_summary.stock_projection_origins.filter((day): day is string => typeof day === "string" && /^\d{4}-\d{2}-\d{2}$/.test(day)) : [];
  const capability = useResource<Page>("/products?page_size=1");
  const unavailable = blocked || loading || !!loadError || !scenario || !forecast || capability.loading || !!capability.error;
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending.current || unavailable || !event.currentTarget.reportValidity()) return;
    const form = new FormData(event.currentTarget);
    const body: Row = { kind, as_of_date: String(form.get("as_of_date")),
      source_import_run_id: forecast?.source_import_run_id, forecast_run_id: forecast?.id, scenario_id: Number(scenario!.id) };
    if (capability.data?.items[0]?.trade_schema_ready === true) body.trade_lifecycle_profile = TRADE_PROFILE;
    if (kind.endsWith("replay")) {
      body.period_start = String(form.get("period_start")); body.period_end = String(form.get("period_end"));
    }
    if (kind === "stock_projection" && availableDates.length && !availableDates.includes(String(body.as_of_date))) {
      setError(new Error("Mốc chốt chưa có đủ dữ liệu trong dự báo cha. Chọn một mốc phù hợp.")); return;
    }
    const serialized = JSON.stringify(body);
    if (retry.current?.body !== serialized) retry.current = { body: serialized, key: crypto.randomUUID() };
    const controller = new AbortController(); pending.current = controller;
    sending.current = true; setBusy(true); onBusyChange?.(true); setError(undefined);
    try {
      const result = await api<{ run_id: string }>("/runs", { method: "POST", signal: controller.signal,
        headers: { "Content-Type": "application/json", "Idempotency-Key": retry.current.key }, body: serialized });
      if (!controller.signal.aborted) {
        retry.current = undefined;
        onCreated(result.run_id, String(scenario!.id));
      }
    } catch (reason) { if (!controller.signal.aborted) setError(reason as Error); }
    finally { sending.current = false; if (!controller.signal.aborted) { setBusy(false); onBusyChange?.(false); } }
  }
  return <form className="scenario-run-form" onSubmit={submit} aria-label="Thiết lập lượt chạy">
    <fieldset disabled={busy}>
      <State loading={loading} error={loadError} />
      <label>Loại công việc
        <select value={kind} onChange={(event) => { setKind(event.target.value); setError(undefined); }}>
          {inventoryKinds.map((value) => <option key={value} value={value}>{label(value)}</option>)}
        </select>
      </label>
      <>
        <label>Dự báo cha đã hoàn tất
          <select name="forecast_run_id" required value={forecast?.id ?? ""} onChange={(event) => setForecastId(event.target.value)}>
            <option value="">Chọn dự báo</option>{forecasts.map((run) => <option key={run.id} value={run.id}>{run.as_of_date} · {run.id.slice(0, 8)} · {String(run.result_summary.origins ?? "—")} mốc</option>)}
          </select>
        </label>
        <p className="notice subtle">{scenario ? `${scenario.name} · phiên bản ${scenario.version}` : "Chọn hoặc lưu kịch bản trước khi chạy."}</p>
        <p className="caption">Kho nhận tự lấy mặc định của từng sản phẩm, không cần chọn lại.</p>
        <State loading={capability.loading} error={capability.error} />
      </>
      <label>Mốc chốt UTC<input key={kind} name="as_of_date" type="date" required
        defaultValue={initialRun?.kind === kind ? initialRun.as_of_date : kind === "stock_projection" ? "2025-10-31" : "2025-09-30"} /></label>
      {kind.endsWith("replay") && <div className="form-grid">
        <label>Từ ngày<input name="period_start" type="date" required defaultValue={initialRun?.period_start ?? "2025-10-01"} /></label>
        <label>Đến ngày<input name="period_end" type="date" required defaultValue={initialRun?.period_end ?? "2025-12-31"} /></label>
      </div>}
      <p className="caption">Tác vụ xử lý nền. Lô nhập là mô phỏng, không gửi đơn đến nhà cung cấp thật.</p>
      {error && <div className="notice error" role="alert">{errorLabel(error)}</div>}
      <button className="primary" disabled={busy || unavailable}>{busy ? "Đang gửi yêu cầu…" : "Chạy kịch bản"}</button>
    </fieldset>
  </form>;
}
