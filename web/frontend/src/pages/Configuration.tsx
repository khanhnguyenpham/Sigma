import { Panel } from "../components/ui/Panel";
import { Table } from "../components/ui/Table";
import { State } from "../components/ui/State";
import { Pager } from "../components/ui/Pager";
import { useConfiguration } from "../hooks/useConfiguration";
import { ConfigurationDialog } from "../components/configuration/ConfigurationDialog";

export function Configuration({ onChanged }: { onChanged: () => void }) {
  const editor = useConfiguration(onChanged);
  return <>
    <div className="page-intro"><h1>Thiết lập tính toán</h1><p>Tùy chọn nâng cao cho việc lập kế hoạch. Cấu hình nhập hàng được quản lý trong từng sản phẩm.</p></div>
    {editor.message && <div className="notice success" role="status">{editor.message}</div>}
    <Panel title="Kịch bản tính toán" note="Dùng cấu hình theo từng sản phẩm khi không khai báo điều chỉnh riêng.">
      <State loading={editor.data.loading} error={editor.data.error} />
      <Table rows={editor.data.data?.items ?? []} columns={[{ key: "name", label: "Tên" }, { key: "description", label: "Ghi chú" }, { key: "version", label: "Phiên bản" }]} />
      <Pager page={editor.page} total={editor.data.data?.total ?? 0} onChange={editor.setPage} />
      <button className="secondary" onClick={() => { editor.setNewScenario(true); editor.setOverrides([]); editor.setReceipts([]); }}>＋ Kịch bản mới</button>
    </Panel>
    {editor.newScenario && <ConfigurationDialog editor={editor} />}
  </>;
}
