import type { ScenarioEditorState, ScenarioSupply } from "../../hooks/useScenarioEditor";
import { ScenarioItemField } from "./ScenarioItemPicker";

export function ScenarioSupplyEditor({ editor }: { editor: ScenarioEditorState }) {
  const { schedule, setSchedule, chooseItem, pickedItems } = editor;
  function update(kind: keyof ScenarioSupply, index: number, key: string, value: unknown) {
    setSchedule(previous => ({ ...previous, [kind]: previous[kind].map((row, i) => i === index ? { ...row, [key]: value } : row) }));
  }
  return <fieldset className="scenario-supply-editor">
    <legend>Lịch ngừng riêng của kịch bản</legend>
    <p className="caption">Chỉ áp dụng cho phiên bản kịch bản này. Để trống để mô phỏng bình thường. Xóa lịch rồi Lưu thiết lập sẽ tạo phiên bản mới; kết quả cũ được giữ nguyên.</p>
    {([['internal_stops', 'Ngừng nhập nội bộ'], ['provider_stops', 'Nhà cung cấp ngừng dịch vụ']] as const).map(([kind, title]) => <fieldset key={kind}>
      <legend>{title}</legend>
      <p className="caption">{kind === 'internal_stops' ? 'Chọn mặt hàng theo nhà mạng; vẫn bán tồn được phép bán.' : 'Chọn sản phẩm theo nhà mạng; áp dụng cho cùng SKU và loại trên tất cả kho.'}</p>
      {schedule[kind].map((row, index) => <div className="scenario-row" key={index}>
        <label>Mặt hàng {title.toLowerCase()} {index + 1}<ScenarioItemField name={`${title.toLowerCase()} ${index+1}`} itemId={row.item_id} item={pickedItems[Number(row.item_id)]} onChoose={()=>chooseItem(kind,index)} /></label>
        <label>Ngày biết lịch UTC<input type="date" required value={String(row.known_on)} onChange={e => update(kind,index,'known_on',e.target.value)} /></label>
        <label>Ngày ngừng UTC<input type="date" required min={String(row.known_on)} value={String(row.effective_on)} onChange={e => update(kind,index,'effective_on',e.target.value)} /></label>
        <label>Lý do ngừng<input required maxLength={1000} value={String(row.reason)} onChange={e => update(kind,index,'reason',e.target.value)} /></label>
        <button type="button" onClick={() => setSchedule(previous => ({ ...previous, [kind]: previous[kind].filter((_,i) => i !== index) }))}>Xóa lịch {index + 1}</button>
      </div>)}
      <div className="scenario-supply-actions"><button type="button" className="scenario-add-stop" onClick={() => chooseItem(kind)}>＋ {title}</button></div>
    </fieldset>)}
    {(schedule.internal_stops.length > 0 || schedule.provider_stops.length > 0) && <div className="scenario-reset-actions"><button type="button" className="scenario-reset-stops" onClick={() => setSchedule({internal_stops:[],provider_stops:[]})}>Xóa tất cả lịch ngừng trong bản nháp</button></div>}
  </fieldset>;
}
