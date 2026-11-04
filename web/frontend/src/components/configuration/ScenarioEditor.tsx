import { useEffect } from "react";
import type { Row } from "../../types/api";
import { useScenarioEditor } from "../../hooks/useScenarioEditor";
import { warehouseName } from "../../utils/warehouse";
import { errorLabel } from "../../utils/labels";
import { ScenarioForm } from "./ScenarioForm";
import { State } from "../ui/State";

export function ScenarioEditor({ scenario, onSaved, onRefresh, onDirty, onBusy }: {
  scenario?: Row; onSaved: (scenario: Row) => void; onRefresh: () => void;
  onDirty: (dirty: boolean) => void; onBusy: (busy: boolean) => void;
}) {
  const editor = useScenarioEditor(scenario, onSaved);
  useEffect(() => { onDirty(editor.dirty); return () => onDirty(false); }, [editor.dirty, onDirty]);
  useEffect(() => { onBusy(editor.busy); return () => onBusy(false); }, [editor.busy, onBusy]);
  return <form className="scenario-editor" onSubmit={editor.save} aria-label="Thiết lập kịch bản">
    {scenario && <p className="caption">Đang xem {String(scenario.name)} · phiên bản {String(scenario.version)}. Lưu thay đổi tạo phiên bản mới.</p>}
    <fieldset disabled={editor.busy}>
      <label>Kho danh mục để chọn mặt hàng
        <select value={editor.warehouse} onChange={(event) => editor.setWarehouse(event.target.value)}>
          <option value="">Chọn kho</option>
          {editor.warehouses.data?.items.map((warehouse) => <option key={String(warehouse.id)} value={String(warehouse.id)}>{warehouseName(warehouse)}</option>)}
        </select>
      </label>
      <State loading={editor.warehouses.loading || editor.itemData.loading} error={editor.warehouses.error ?? editor.itemData.error} />
      <p className="caption">Kho trên dùng tìm mặt hàng. Kho nhận hàng tự lấy mặc định của từng sản phẩm khi tạo lượt chạy.</p>
      <ScenarioForm editor={editor} />
      {editor.error && <div role="alert" className="notice error">{errorLabel(editor.error)}</div>}
      {editor.uncertain && <p className="notice">Kết quả lưu chưa rõ. Tải lại danh sách để đối chiếu trước khi chọn phiên bản hoặc tạo bản nháp khác.</p>}
      <div className="form-actions">
        <button className="primary" disabled={editor.busy || editor.uncertain || (!!scenario && !editor.dirty)}>{editor.busy ? "Đang lưu…" : "Lưu thiết lập"}</button>
        {editor.uncertain && <button type="button" onClick={onRefresh}>Tải lại danh sách kịch bản</button>}
      </div>
    </fieldset>
  </form>;
}
