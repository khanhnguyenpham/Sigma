import { useEffect, useState } from "react";
import type { AppContextState } from "../hooks/useAppContext";
import type { Page, Row, Run } from "../types/api";
import { apiAllPages } from "../services/http";
import { useResource } from "../hooks/useResource";
import { useTradeNavigation } from "../hooks/useTradeNavigation";
import { ScenarioEditor } from "../components/configuration/ScenarioEditor";
import { ScenarioResults } from "../components/configuration/ScenarioResults";
import { C00Evaluation } from "../components/alerts/C00Evaluation";
import { RunForm } from "../components/configuration/RunForm";
import { RunRetry } from "../components/dialogs/RunRetry";
import { Panel } from "../components/ui/Panel";
import { State } from "../components/ui/State";
import { Table } from "../components/ui/Table";
import { Pager } from "../components/ui/Pager";
import { label } from "../utils/labels";
import { inventoryKinds } from "../config/navigation";
import { query } from "../utils/url";

export function Scenarios({ app }: { app: AppContextState }) {
  const [directoryRevision, setDirectoryRevision] = useState(0), [historyRevision, setHistoryRevision] = useState(0);
  const [editorRevision, setEditorRevision] = useState(0), [historyPage, setHistoryPage] = useState(1);
  const [saved, setSaved] = useState<Row>(), [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false), [sending, setSending] = useState(false), [retrying, setRetrying] = useState(false);
  const [kind, setKind] = useState("stock_projection");
  const busy = saving || sending || retrying;
  useTradeNavigation(dirty, busy, () => {}, false);
  const directory = useResource<Page>("/scenarios?page_size=100", true, directoryRevision, apiAllPages);
  const sourceParents = useResource<Page<Run>>("/runs?kind=source_import&status=complete&page_size=100", false, directoryRevision, apiAllPages<Run>);
  const forecastParents = useResource<Page<Run>>("/runs?kind=forecast&status=complete&page_size=100", false, directoryRevision, apiAllPages<Run>);
  const run = app.selectedResource.data?.id === app.ctx.runId ? app.selectedResource.data : undefined;
  const scenarioId = app.ctx.scenarioId || (run?.scenario_id ? String(run.scenario_id) : "");
  const scenarios = [...(directory.data?.items ?? [])];
  if (saved && !scenarios.some((row) => String(row.id) === String(saved.id))) scenarios.push(saved);
  const scenario = scenarios.find((row) => String(row.id) === scenarioId);
  const mismatch = !!run && !!app.ctx.scenarioId && app.ctx.scenarioId !== String(run.scenario_id ?? "");
  const missing = !!scenarioId && !directory.loading && !scenario;
  const history = useResource<Page<Run>>(!scenarioId || /^\d+$/.test(scenarioId)
    ? `/runs?${query({ scenario_id: scenarioId, page: historyPage, page_size: 10 })}` : null, false, historyRevision);
  useEffect(() => { setHistoryPage(1); }, [scenarioId]);
  useEffect(() => {
    setHistoryRevision((value) => value + 1);
    if (run) {
      if (!app.ctx.scenarioId && run.scenario_id) app.setCtx((current) => ({ ...current, scenarioId: String(run.scenario_id) }));
    }
  }, [run?.id, run?.status]);
  useEffect(() => { if (run) setKind(run.kind); }, [run?.id]);
  function refresh() { setDirectoryRevision((value) => value + 1); setHistoryRevision((value) => value + 1); }
  function savedScenario(row: Row) { setDirty(false); setSaved(row); app.scenarioSaved(String(row.id)); refresh(); }
  function createDraft() { if (app.chooseScenario("")) { setEditorRevision((value) => value + 1); setDirty(false); } }
  function created(id: string, selectedScenario = inventoryKinds.includes(kind) ? scenarioId : "") {
    app.scenarioRunCreated(id, selectedScenario);
    setHistoryRevision((value) => value + 1);
  }
  const active = !!run && ["queued", "running"].includes(run.status);
  const parentLoading = kind === "source_import" ? false : kind === "forecast" ? sourceParents.loading : forecastParents.loading;
  const parentError = kind === "source_import" ? undefined : kind === "forecast" ? sourceParents.error : forecastParents.error;
  const progress = run?.result_summary;
  const phase = ({ import_daily_sales: "Đang nhập dữ liệu ngày", validation: "Đang đánh giá dự báo", test: "Đang đánh giá dự báo",
    future: "Đang tạo dự báo", fixed_top10_replay: "Đang xử lý dự báo tuyến", allocation: "Đang phân bổ dự báo", simulation: "Đang tính kế hoạch" } as Record<string, string>)[String(progress?.phase)] ?? label(run?.status ?? "");
  const completed = progress?.completed_jobs ?? progress?.completed_origins ?? progress?.completed_windows;
  const total = progress?.total_jobs ?? progress?.total_origins ?? progress?.total_windows;
  return <div className="scenario-workspace">
    <div className="page-heading"><div><h1>Kịch bản</h1><p>Thiết lập, chạy và xem kết quả ngay tại đây.</p></div>
      <button type="button" className="secondary" onClick={() => app.navigate("overview")}>← Tổng quan</button></div>
    <C00Evaluation />
    <Panel title="Chọn kịch bản" note="Mỗi phiên bản đã lưu được giữ riêng với các lượt chạy của nó.">
      <div className="scenario-picker">
        <label>Kịch bản / phiên bản
          <select value={scenarioId} disabled={busy || directory.loading} onChange={(event) => app.chooseScenario(event.target.value)}>
            <option value="">Tạo kịch bản mới</option>
            {scenarios.map((row) => <option key={String(row.id)} value={String(row.id)}>{String(row.name)} · v{String(row.version)}</option>)}
            {missing && <option value={scenarioId}>Không tìm thấy phiên bản trong liên kết</option>}
          </select>
        </label>
        <button type="button" className="secondary" disabled={busy} onClick={createDraft}>＋ Tạo kịch bản mới</button>
      </div>
      <State loading={directory.loading} error={directory.error} />
      {missing && <p className="notice error" role="alert">Không tìm thấy kịch bản trong liên kết. Hãy chọn phiên bản khác; trang không tự đổi lựa chọn.</p>}
      {mismatch && <div className="notice error" role="alert">Kịch bản trong liên kết không khớp lượt chạy.
        <button type="button" onClick={() => app.openScenarios(run!.id, String(run!.scenario_id ?? ""))}>Mở đúng kịch bản của lượt chạy</button></div>}
    </Panel>
    <div className="scenario-setup-grid">
      <Panel title="Thiết lập kịch bản" note="Lưu thiết lập trước khi chạy. Lưu không tự tạo công việc.">
        {(!app.ctx.runId || run) && (!scenarioId || scenario) && !missing && <ScenarioEditor key={`${scenarioId}:${editorRevision}:${app.scenarioRevision}`} scenario={scenario}
          onSaved={savedScenario} onRefresh={refresh} onDirty={setDirty} onBusy={setSaving} />}
      </Panel>
      <Panel title="Thiết lập lượt chạy" note="Kho nhận theo mặc định từng sản phẩm, được chốt khi nhận lượt chạy.">
        {dirty && <p className="notice" role="status">Bản nháp chưa lưu chưa áp dụng cho kết quả đang xem.</p>}
        {(!app.ctx.runId || run) && <RunForm key={`${scenarioId}:${run?.id ?? "new"}`} initialRun={run} runs={[...(sourceParents.data?.items ?? []), ...(forecastParents.data?.items ?? [])]}
          scenario={scenario} blocked={dirty || saving || active || mismatch || missing || (inventoryKinds.includes(kind) && (!!directory.error || directory.loading))}
          loading={parentLoading} loadError={parentError} onKindChange={setKind} onBusyChange={setSending} onCreated={created} />}
      </Panel>
    </div>
    <Panel title="Tiến độ và kết quả" note="Dữ liệu của đúng lượt chạy đã chọn; thay thiết lập hiện tại không sửa kết quả đã lưu.">
      {!app.ctx.runId ? <p className="caption">Lưu/chọn kịch bản rồi bấm Chạy kịch bản để bắt đầu.</p> : <>
        <State loading={!run && app.selectedResource.loading} error={app.selectedResource.error} />
        {run && !mismatch && <>
          <dl className="scenario-run-meta">
            <div><dt>Lượt chạy</dt><dd>{run.id}</dd></div><div><dt>Công việc</dt><dd>{label(run.kind)}</dd></div>
            <div><dt>Trạng thái</dt><dd>{label(run.status)}</dd></div><div><dt>Mốc UTC</dt><dd>{run.as_of_date}</dd></div>
            {run.scenario_id && <div><dt>Kịch bản đã chốt</dt><dd>{String(run.scenario_name ?? scenario?.name ?? "—")} · v{String(run.scenario_version ?? scenario?.version ?? "—")}</dd></div>}
            {run.source_import_run_id && <div><dt>Nguồn</dt><dd>{run.source_import_run_id}</dd></div>}
            {run.forecast_run_id && <div><dt>Dự báo cha</dt><dd>{run.forecast_run_id}</dd></div>}
            {run.retry_of_run_id && <div><dt>Thử lại từ lượt</dt><dd><button type="button" className="text-button" onClick={() => app.openScenarios(run.retry_of_run_id!, String(run.scenario_id ?? ""))}>{run.retry_of_run_id}</button></dd></div>}
            {run.period_start && <div><dt>Kỳ chạy</dt><dd>{run.period_start} → {run.period_end}</dd></div>}
          </dl>
          {run.scenario_settings && Object.keys(run.scenario_settings).length > 0 && <details className="advanced-section">
            <summary>Thiết lập đã chốt của lượt chạy</summary>
            <p>Tồn đầu: {String(run.scenario_settings.cover_days ?? "—")} ngày phủ · Hệ số tồn an toàn: {String(run.scenario_settings.safety_multiplier ?? "—")}.</p>
            <p>{run.receiving_warehouse_profile ? "Kho nhận được chốt theo mặc định từng sản phẩm khi tạo lượt chạy; xem kho trong bảng kết quả." : "Kho theo cấu hình đã chốt của lượt chạy lịch sử."}</p>
            {Array.isArray(run.scenario_settings.policy_overrides) && <Table rows={run.scenario_settings.policy_overrides as Row[]}
              columns={[{ key: "item_id", label: "Mặt hàng" }, { key: "configured_rop_floor", label: "ROP điều chỉnh" }, { key: "safety_days", label: "Ngày tồn an toàn" }, { key: "warning_horizon_days", label: "Ngày cảnh báo" }]} />}
            {Array.isArray(run.scenario_settings.receipts_initial) && <Table rows={run.scenario_settings.receipts_initial as Row[]}
              columns={[{ key: "item_id", label: "Mặt hàng" }, { key: "ordered_on", label: "Ngày đặt" }, { key: "eta", label: "Dự kiến nhận" }, { key: "ordered_qty", label: "Số lượng" }]} />}
          </details>}
          {active && <div className="notice" role="status">{phase}{completed != null && total != null ? ` · ${completed}/${total}` : ""}. Bạn có thể rời trang và quay lại theo dõi.</div>}
          {run.status === "failed" && <div className="notice error" role="alert"><p>Lượt chạy chưa hoàn tất. Mã lỗi: {run.error_code ?? "Chưa có chi tiết"}.</p>
            <p>Thử lại tạo lượt mới theo cấu hình và kho mặc định hiện tại; lượt cũ được giữ.</p>
            <RunRetry key={run.id} id={run.id} disabled={dirty || busy} onBusyChange={setRetrying} onCreated={(id) => created(id, String(run.scenario_id ?? ""))} /></div>}
          {run.status === "invalidated" && <p className="notice error" role="alert">Kết quả lượt này không còn hợp lệ. Tạo lượt chạy mới để tiếp tục.</p>}
          {run.status === "complete" && <><p className="notice success" role="status">Đã chạy xong. Kết quả hiển thị bên dưới.</p><ScenarioResults key={run.id} app={app} run={run} /></>}
        </>}
      </>}
    </Panel>
    <Panel title={scenarioId ? "Các lượt đã chạy của phiên bản này" : "Các lượt chạy gần đây"}>
      <State loading={history.loading} error={history.error} empty={!history.loading && !history.error && !history.data?.items.length} />
      {history.data && <><Table rows={history.data.items.map((row) => ({ ...row }))} columns={[
        { key: "id", label: "Lượt chạy", render: (_value, row) => <button className="text-button" onClick={() => app.openScenarios(String(row.id), row.scenario_id ? String(row.scenario_id) : "")}>{String(row.id).slice(0, 8)}</button> },
        { key: "kind", label: "Công việc", render: (value) => label(String(value)) },
        { key: "status", label: "Trạng thái", render: (value) => label(String(value)) },
        { key: "as_of_date", label: "Mốc UTC" },
      ]} /><Pager page={historyPage} total={history.data.total} onChange={setHistoryPage} /></>}
    </Panel>
  </div>;
}
