import { useRef, useState } from "react";
import {
  api,
  type Run,
  type Page,
  type Row,
  label,
  errorLabel,
} from "../api/client";
import { useResource, State, useDialogFocus } from "./common";
export function RunDialog({
  runs,
  onClose,
  onCreated,
}: {
  runs: Run[];
  onClose: () => void;
  onCreated: (id: string) => void;
}) {
  useDialogFocus(true, onClose);
  const [kind, setKind] = useState("stock_projection"),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<Error>();
  const sending = useRef(false),
    retry = useRef<{ body: string; key: string } | undefined>(undefined);
  const scenarios = useResource<Page>("/scenarios?page_size=100");
  const sources = runs.filter(
    (r) => r.kind === "source_import" && r.status === "complete",
  );
  const forecasts = runs.filter(
    (r) => r.kind === "forecast" && r.status === "complete",
  );
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (sending.current) return;
    const form = new FormData(e.currentTarget);
    const forecast = forecasts.find(
      (r) => r.id === String(form.get("forecast_run_id")),
    );
    const source =
      kind === "forecast" || kind === "source_import"
        ? String(form.get("source_import_run_id"))
        : forecast?.source_import_run_id;
    let body: Row = { kind, as_of_date: String(form.get("as_of_date")) };
    if (kind === "source_import") body.source_key = "orders_snapshot";
    else body.source_import_run_id = source;
    if (kind === "forecast") body.mode = "replay";
    if (["policy_replay", "alert_replay", "stock_projection"].includes(kind)) {
      body.forecast_run_id = forecast?.id;
      body.scenario_id = Number(form.get("scenario_id"));
    }
    if (kind.endsWith("replay")) {
      body.period_start = String(form.get("period_start"));
      body.period_end = String(form.get("period_end"));
    }
    const serialized = JSON.stringify(body);
    if (retry.current?.body !== serialized)
      retry.current = { body: serialized, key: crypto.randomUUID() };
    sending.current = true;
    setBusy(true);
    setError(undefined);
    try {
      const result = await api<{ run_id: string }>("/runs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": retry.current.key,
        },
        body: serialized,
      });
      onCreated(result.run_id);
    } catch (e) {
      setError(e as Error);
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }
  return (
    <div className="modal-shade">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="run-title"
      >
        <button
          className="close"
          aria-label="Đóng tạo lượt chạy"
          onClick={onClose}
        >
          ×
        </button>
        <span className="eyebrow">PHƯƠNG ÁN MỚI</span>
        <h2 id="run-title">Giữ nguồn rõ, chạy có kiểm chứng.</h2>
        <form onSubmit={submit}>
          <label>
            Loại công việc
            <select
              aria-label="Loại công việc"
              value={kind}
              onChange={(e) => setKind(e.target.value)}
            >
              {[
                "stock_projection",
                "policy_replay",
                "alert_replay",
                "forecast",
                "source_import",
              ].map((k) => (
                <option value={k} key={k}>
                  {label(k)}
                </option>
              ))}
            </select>
          </label>
          {kind === "forecast" && (
            <label>
              Nguồn đã audit
              <select name="source_import_run_id" required>
                {sources.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.as_of_date} · {r.id.slice(0, 8)}
                  </option>
                ))}
              </select>
            </label>
          )}
          {["policy_replay", "alert_replay", "stock_projection"].includes(
            kind,
          ) && (
            <>
              <label>
                Dự báo cha đã hoàn tất
                <select name="forecast_run_id" required>
                  {forecasts.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.as_of_date} · {r.id.slice(0, 8)} ·{" "}
                      {String(r.result_summary.routes ?? "—")} tuyến ·{" "}
                      {String(r.result_summary.origins ?? "—")} mốc
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Kịch bản
                <select name="scenario_id" required>
                  {scenarios.data?.items.map((r) => (
                    <option value={String(r.id)} key={String(r.id)}>
                      {String(r.name)} · v{String(r.version)}
                    </option>
                  ))}
                </select>
              </label>
              <State loading={scenarios.loading} error={scenarios.error} />
            </>
          )}
          <label>
            Mốc chốt UTC
            <input
              key={kind}
              name="as_of_date"
              type="date"
              required
              defaultValue={
                kind === "stock_projection"
                  ? "2025-10-31"
                  : kind.endsWith("replay")
                    ? "2025-09-30"
                    : "2025-12-31"
              }
            />
          </label>
          {kind.endsWith("replay") && (
            <div className="form-grid">
              <label>
                Từ ngày
                <input
                  name="period_start"
                  type="date"
                  defaultValue="2025-10-01"
                  required
                />
              </label>
              <label>
                Đến ngày
                <input
                  name="period_end"
                  type="date"
                  defaultValue="2025-12-31"
                  required
                />
              </label>
            </div>
          )}
          <div className="notice subtle">
            L7 / R1 / H14 cố định. Tồn và nhập là mô phỏng. Forecast replay chạy
            validation → khóa lựa chọn → test; không chọn lại theo test. Worker
            xử lý nền, màn hình không phải chờ kết nối HTTP dài.
          </div>
          {error && (
            <div role="alert" className="notice error">
              {errorLabel(error)}
            </div>
          )}
          <button className="primary" disabled={busy}>
            {busy ? "Đang gửi yêu cầu…" : "Bắt đầu lượt chạy"}
          </button>
        </form>
      </section>
    </div>
  );
}
