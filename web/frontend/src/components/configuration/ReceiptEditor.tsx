import { type ConfigurationState } from "../../hooks/useConfiguration";

import { ItemSelect } from "./ItemSelect";

export function ReceiptEditor({ editor }: { editor: ConfigurationState }) {
  const {
    receipts,
    setReceipts,
    update,
    updateReceiptDate,
    warehouse,
    itemData,
    itemOptions,
  } = editor;
  return (
    <fieldset>
      <legend>Lô đang về đã biết tại origin</legend>
      {receipts.map((row, index) => (
        <div className="scenario-row" key={index}>
          <label>
            Mặt hàng
            {
              <ItemSelect
                name={"receipt_item_" + index}
                value={row.item_id}
                onChange={(id) =>
                  update(receipts, setReceipts, index, "item_id", id)
                }
                itemOptions={itemOptions}
              />
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
        disabled={!warehouse || itemData.loading || !itemOptions.length}
        onClick={() =>
          setReceipts([
            ...receipts,
            {
              item_id: Number(itemOptions[0]?.id ?? 0),
              ordered_on: "2025-09-30",
              eta: "2025-10-07",
              ordered_qty: 10,
              lot_key: crypto.randomUUID(),
            },
          ])
        }
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
