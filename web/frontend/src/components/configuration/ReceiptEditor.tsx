import { type ScenarioEditorState } from "../../hooks/useScenarioEditor";

import { ScenarioItemField } from "./ScenarioItemPicker";

export function ReceiptEditor({ editor }: { editor: ScenarioEditorState }) {
  const {
    receipts,
    setReceipts,
    update,
    updateReceiptDate,
    chooseItem,
    pickedItems,
  } = editor;
  return (
    <fieldset>
      <legend>Lô đang về đã biết tại origin</legend>
      {receipts.map((row, index) => (
        <div className="scenario-row" key={index}>
          <label>
            Mặt hàng
            {
              <ScenarioItemField name={`lô đang về ${index+1}`} itemId={row.item_id} item={pickedItems[Number(row.item_id)]} onChoose={()=>chooseItem('receipt',index)} />
            }
          </label>
          <label>
            Ngày đặt
            <input
              type="date"
              required
              value={String(row.ordered_on)}
              onInput={(e) => updateReceiptDate(index, e.currentTarget.value)}
              onChange={(e) => updateReceiptDate(index, e.currentTarget.value)}
            />
          </label>
          <label>
            ETA = ngày đặt +7
            <input readOnly value={String(row.eta)} />
          </label>
          <label>
            Số lượng
            <input
              type="number"
              required
              min="1"
              step="1"
              value={Number(row.ordered_qty)}
              onChange={(e) =>
                update(
                  receipts,
                  setReceipts,
                  index,
                  "ordered_qty",
                  Number(e.target.value),
                )
              }
            />
          </label>
          <button
            type="button"
            onClick={() => setReceipts(receipts.filter((_, i) => i !== index))}
          >
            Xóa lô
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={() => chooseItem('receipt')}
      >
        ＋ Lô đang về
      </button>
      <p className="caption">
        Danh sách trống nghĩa không có lô đầu kỳ. Lô đặt sau origin hoặc trùng
        mã sẽ bị từ chối.
      </p>
    </fieldset>
  );
}
