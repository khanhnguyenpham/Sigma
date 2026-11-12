import { useEffect, useRef, useState } from "react";
import { api, apiAllPages } from "../../services/http";
import type { Run, Page, Row } from "../../types/api";
import { label, errorLabel } from "../../utils/labels";
import { useResource } from "../../hooks/useResource";
import { inventoryKinds } from "../../config/navigation";
import { State } from "../ui/State";
import { TRADE_PROFILE } from "../../utils/trade";
import { observation_end as sourceObservationEnd, source_key as registeredSourceKey } from "../../../../backend/configs/m3-profile.json";

export function RunForm({ runs, onCreated, scenario, blocked = false, loading = false, loadError,
  initialRun, onKindChange, onBusyChange }: {
  runs: Run[]; onCreated: (id: string, scenarioId?: string) => void; scenario?: Row;
  blocked?: boolean; loading?: boolean; loadError?: Error; initialRun?: Run;
  onKindChange?: (kind: string) => void; onBusyChange?: (busy: boolean) => void;
}) {
  const importedSourceId = initialRun?.kind === "source_import" ? initialRun.id : undefined;
  const [kind, setKind] = useState(importedSourceId ? "forecast" :
    initialRun && inventoryKinds.includes(initialRun.kind) ? initialRun.kind : "stock_projection");
  useEffect(() => { onKindChange?.(kind); }, [kind, onKindChange]);
  const [busy, setBusy] = useState(false), [error, setError] = useState<Error>();
  const sending = useRef(false), retry = useRef<{ body: string; key: string } | undefined>(undefined);
  const pending = useRef<AbortController | undefined>(undefined);
  useEffect(() => () => pending.current?.abort(), []);
  const [forecastId, setForecastId] = useState(initialRun?.forecast_run_id ?? "");
  const [sourceId, setSourceId] = useState(importedSourceId ?? initialRun?.source_import_run_id ?? "");
  const importingSource = kind === "source_import";
  const creatingForecast = kind === "forecast";
  const planning = inventoryKinds.includes(kind);
  const sourceRevision = importedSourceId && initialRun?.status === "complete" ? 1 : 0;
  const sourceParents = useResource<Page<Run>>(creatingForecast ? "/runs?kind=source_import&status=complete&page_size=100" : null,
    false, sourceRevision, apiAllPages<Run>);
  const sources = sourceParents.data?.items ?? [];
  const source = sourceId ? sources.find((run) => run.id === sourceId) : sources[0];
  const forecasts = runs.filter((run) => run.kind === "forecast" && run.status === "complete");
  const forecast = forecastId ? forecasts.find((run) => run.id === forecastId)
    : forecasts.find((run) => Number(run.result_summary.origins) > 1) ?? forecasts[0];
  const availableDates = Array.isArray(forecast?.result_summary.stock_projection_origins)
    ? forecast.result_summary.stock_projection_origins.filter((day): day is string => typeof day === "string" && /^\d{4}-\d{2}-\d{2}$/.test(day)) : [];
  const capability = useResource<Page>(planning ? "/products?page_size=1" : null);
  const parentLoading = creatingForecast ? sourceParents.loading : planning && loading;
  const parentError = creatingForecast ? sourceParents.error : planning ? loadError : undefined;
  const unavailable = blocked || parentLoading || !!parentError || (creatingForecast && !source) ||
    (planning && (!scenario || !forecast || capability.loading || !!capability.error));
  const submitLabel = importingSource ? "Tạo nguồn dữ liệu" : creatingForecast ? "Chạy dự báo" : "Chạy kịch bản";
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending.current || unavailable || !event.currentTarget.reportValidity()) return;
    const form = new FormData(event.currentTarget);
    let body: Row;
    if (importingSource) {
      body = { kind, as_of_date: sourceObservationEnd, source_key: registeredSourceKey };
    } else if (creatingForecast) {
      body = { kind, mode: "replay", as_of_date: source!.observation_end, source_import_run_id: source!.id };
    } else {
      body = { kind, as_of_date: String(form.get("as_of_date")), source_import_run_id: forecast?.source_import_run_id,
        forecast_run_id: forecast?.id, scenario_id: Number(scenario!.id) };
    }
    if (planning && capability.data?.items[0]?.trade_schema_ready === true) {
      body.trade_lifecycle_profile = TRADE_PROFILE;
      body.scenario_supply_profile = "scenario_supply_v1";
    }
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
        onCreated(result.run_id, planning ? String(scenario!.id) : "");
      }
    } catch (reason) { if (!controller.signal.aborted) setError(reason as Error); }
    finally { sending.current = false; if (!controller.signal.aborted) { setBusy(false); onBusyChange?.(false); } }
  }
  return <form className="scenario-run-form" onSubmit={submit} aria-label="Thiết lập lượt chạy">
    <fieldset disabled={busy}>
      <State loading={parentLoading} error={parentError} />
      <label>Loại công việc
        <select value={kind} onChange={(event) => { setKind(event.target.value); setError(undefined); }}>
          <optgroup label="Chuẩn bị dữ liệu">
            <option value="source_import">Tạo nguồn dữ liệu</option>
            <option value="forecast">Tạo dự báo</option>
          </optgroup>
          <optgroup label="Chạy kế hoạch">
            {inventoryKinds.map((value) => <option key={value} value={value}>{label(value)}</option>)}
          </optgroup>
        </select>
      </label>
      {importingSource && <>
        <label>Mốc chốt UTC<input type="date" readOnly value={sourceObservationEnd} /></label>
        <p className="caption">Nhập bộ dữ liệu bán hàng đã đăng ký. Khi nhập xong, nguồn sẽ xuất hiện trong mục Tạo dự báo.</p>
      </>}
      {creatingForecast && <>
        <label>Nguồn đã hoàn tất
          <select name="source_import_run_id" required value={source?.id ?? ""} onChange={(event) => setSourceId(event.target.value)}>
            <option value="">Chọn nguồn</option>
            {sources.map((run) => <option key={run.id} value={run.id}>{run.observation_end} · {run.id.slice(0, 8)}</option>)}
          </select>
        </label>
        {!parentLoading && !parentError && !sources.length && <p className="notice">Cần có lượt nhập nguồn hoàn tất để tạo dự báo.</p>}
        <label>Mốc chốt UTC<input type="date" readOnly value={source?.observation_end ?? ""} /></label>
        <p className="caption">Worker tạo bộ dự báo hồi cứu theo nguồn đã chọn. Khi hoàn tất, bộ dự báo có thể dùng cho nhiều kịch bản.</p>
      </>}
      {planning && <>
        <p className="notice subtle">Lượt mới chỉ áp dụng lịch ngừng đã lưu trong phiên bản kịch bản đang chọn. Không có lịch nghĩa là nhập và bán bình thường theo chính sách.</p>
        <label>Dự báo cha đã hoàn tất
          <select name="forecast_run_id" required value={forecast?.id ?? ""} onChange={(event) => setForecastId(event.target.value)}>
            <option value="">Chọn dự báo</option>{forecasts.map((run) => <option key={run.id} value={run.id}>{run.as_of_date} · {run.id.slice(0, 8)} · {String(run.result_summary.origins ?? "—")} mốc</option>)}
          </select>
        </label>
        <p className="notice subtle">{scenario ? `${scenario.name} · phiên bản ${scenario.version}` : "Chọn hoặc lưu kịch bản trước khi chạy."}</p>
        <p className="caption">Kho nhận tự lấy mặc định của từng sản phẩm, không cần chọn lại.</p>
        <State loading={capability.loading} error={capability.error} />
        <label>Mốc chốt UTC<input key={kind} name="as_of_date" type="date" required
          defaultValue={initialRun?.kind === kind ? initialRun.as_of_date : kind === "stock_projection" ? "2025-10-31" : "2025-09-30"} /></label>
      </>}
      {kind.endsWith("replay") && <div className="form-grid">
        <label>Từ ngày<input name="period_start" type="date" required defaultValue={initialRun?.period_start ?? "2025-10-01"} /></label>
        <label>Đến ngày<input name="period_end" type="date" required defaultValue={initialRun?.period_end ?? "2025-12-31"} /></label>
      </div>}
      {planning && <p className="caption">Tác vụ xử lý nền. Lô nhập là mô phỏng, không gửi đơn đến nhà cung cấp thật.</p>}
      {error && <div className="notice error" role="alert">{errorLabel(error)}</div>}
      <button className="primary" disabled={busy || unavailable}>{busy ? "Đang gửi yêu cầu…" : submitLabel}</button>
    </fieldset>
  </form>;
}
