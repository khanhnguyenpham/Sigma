import { useEffect } from "react";
import type { Row } from "../../types/api";
import { useScenarioEditor } from "../../hooks/useScenarioEditor";
import { errorLabel } from "../../utils/labels";
import { ScenarioForm } from "./ScenarioForm";
import { ScenarioItemPicker } from "./ScenarioItemPicker";

export function ScenarioEditor({ scenario, onSaved, onRefresh, onDirty, onBusy }: {
  scenario?: Row; onSaved: (scenario: Row) => void; onRefresh: () => void;
  onDirty: (dirty: boolean) => void; onBusy: (busy: boolean) => void;
}) {
  const editor = useScenarioEditor(scenario, onSaved);
  useEffect(() => { onDirty(editor.dirty); return () => onDirty(false); }, [editor.dirty, onDirty]);
  useEffect(() => { onBusy(editor.busy || !!editor.picker); return () => onBusy(false); }, [editor.busy, !!editor.picker, onBusy]);
  const selectedRows=editor.picker?.kind==='override' ? editor.overrides : editor.picker?.kind==='receipt' ? [] : editor.picker ? editor.schedule[editor.picker.kind] : [];
  const titles={override:'Chọn mặt hàng điều chỉnh',receipt:'Chọn mặt hàng cho lô đang về',internal_stops:'Chọn mặt hàng ngừng nhập nội bộ',provider_stops:'Chọn sản phẩm nhà cung cấp ngừng dịch vụ'};
  return <><form className="scenario-editor" onSubmit={editor.save} aria-label="Thiết lập kịch bản">
    {scenario && <p className="caption">Đang xem {String(scenario.name)} · phiên bản {String(scenario.version)}. Lưu thay đổi tạo phiên bản mới.</p>}
    <fieldset disabled={editor.busy || !!editor.picker}>
      <ScenarioForm editor={editor} />
      {editor.error && <div role="alert" className="notice error">{errorLabel(editor.error)}</div>}
      {editor.uncertain && <p className="notice">Kết quả lưu chưa rõ. Tải lại danh sách để đối chiếu trước khi chọn phiên bản hoặc tạo bản nháp khác.</p>}
      <div className="form-actions">
        <button className="primary" disabled={editor.busy || editor.uncertain || (!!scenario && !editor.dirty)}>{editor.busy ? "Đang lưu…" : "Lưu thiết lập"}</button>
        {editor.uncertain && <button type="button" onClick={onRefresh}>Tải lại danh sách kịch bản</button>}
      </div>
    </fieldset>
  </form>{editor.picker && <ScenarioItemPicker title={titles[editor.picker.kind]} productWide={editor.picker.kind==='provider_stops'}
    excludedIds={selectedRows.filter((_,index)=>index!==editor.picker?.index).map(row=>Number(row.item_id))}
    onChoose={editor.itemChosen} onClose={()=>editor.setPicker(undefined)} />}</>;
}
