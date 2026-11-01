import type { ConfigurationState } from "../../hooks/useConfiguration";
import { errorLabel } from "../../utils/labels";
import { warehouseName } from "../../utils/warehouse";
import { ScenarioForm } from "./ScenarioForm";

export function ConfigurationDialog({ editor }: { editor: ConfigurationState }) {
  return <div className="modal-shade"><section className="modal" role="dialog" aria-modal="true" aria-labelledby="config-title">
    <button className="close" aria-label="Đóng cấu hình" onClick={() => editor.setNewScenario(false)}>×</button>
    <h2 id="config-title">Kịch bản tính toán</h2>
    <form onSubmit={editor.save}>
      <label>Kho để chọn mặt hàng<select value={editor.warehouse} onChange={(event) => editor.setWarehouse(event.target.value)}><option value="">Chọn kho</option>{editor.warehouses.data?.items.map((w) => <option key={String(w.id)} value={String(w.id)}>{warehouseName(w)}</option>)}</select></label>
      <ScenarioForm editor={editor} />
      <button className="primary" disabled={editor.busy}>{editor.busy ? "Đang lưu…" : "Lưu phiên bản mới"}</button>
      {editor.error && <div role="alert" className="notice error">{errorLabel(editor.error)}</div>}
    </form>
  </section></div>;
}
