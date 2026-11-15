import { useState, type FormEvent } from "react";
import { Dialog } from "../components/ui/Dialog";
import { State } from "../components/ui/State";
import { WriteError } from "./WriteError";
import { useResource } from "../hooks/useResource";
import { useTradeNavigation } from "../hooks/useTradeNavigation";
import { ProductPicker } from "./ProductPicker";
import { refreshOperations, useOperationWrite } from "./useOperationWrite";
import { qty, type Position, type Warehouse } from "./types";

export function MovementEditor({ kind, initial, warehouses, today, onClose }: { kind: "issue" | "count"; initial?: Position; warehouses: Warehouse[]; today: string; onClose: () => void }) {
  const [warehouse, setWarehouse] = useState(initial?.warehouse_id ?? warehouses[0]?.id ?? 0), [item, setItem] = useState(initial?.item_id ?? 0);
  const [quantity, setQuantity] = useState(""), [dirty, setDirty] = useState(false);
  const position = useResource<Position>(warehouse && item ? `/operations/stock/${warehouse}/${item}` : null);
  const write = useOperationWrite(), navigation = useTradeNavigation(dirty, write.busy, onClose, false);
  const valid = quantity !== "" && Number.isSafeInteger(Number(quantity)) && Number(quantity) >= (kind === "issue" ? 1 : 0);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!valid || !position.data || position.loading || position.error) return;
    const fields = new FormData(event.currentTarget);
    const result = await write.send(kind === "issue" ? "/issues" : "/counts", { warehouse_id: warehouse, item_id: item, quantity: Number(quantity), expected_balance_version: position.data.version, occurred_on: fields.get("occurred_on"), external_ref: fields.get("external_ref"), reason: fields.get("reason") });
    if (result) { navigation.finish(); refreshOperations(); onClose(); }
  }
  return <Dialog title={kind === "issue" ? "Xuất kho" : "Ghi nhận kiểm kê"} onClose={navigation.close} busy={write.busy} className="operations-form-dialog">
    <form onSubmit={(event) => void save(event)} onChange={() => setDirty(true)}><fieldset disabled={write.busy}><div className="operations-form-fields"><WriteError error={write.error} />
      <label>Kho hàng<select required value={warehouse || ""} onChange={(event) => { setWarehouse(Number(event.target.value)); setQuantity(""); }}><option value="">Chọn kho</option>{warehouses.map((row) => <option key={row.id} value={row.id}>{row.code} · {row.name}</option>)}</select></label>
      {!item ? <ProductPicker includeInactive onPick={(product) => { setItem(product.id); setDirty(true); }} /> : <><State loading={position.loading} error={position.error} />{position.data && !position.loading && <div className="ops-balance-card"><strong>{position.data.name}</strong><p>Tồn sổ: <strong>{qty(position.data.on_hand_qty)}</strong></p></div>}
        {!initial && <button type="button" onClick={() => { setItem(0); setQuantity(""); }}>Chọn sản phẩm khác</button>}
      </>}
      <label>{kind === "issue" ? "Số lượng xuất" : "Số lượng đếm thực tế"}<input type="number" required min={kind === "issue" ? 1 : 0} max={kind === "issue" ? position.data?.on_hand_qty ?? 0 : Number.MAX_SAFE_INTEGER} step={1} value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label>
      {valid && position.data && <p aria-live="polite">{kind === "issue" ? <>Tồn sau xuất: <strong>{qty(position.data.on_hand_qty - Number(quantity))}</strong></> : <>Chênh lệch kiểm kê: <strong>{qty(Number(quantity) - position.data.on_hand_qty)}</strong>. Tồn sau ghi sổ: <strong>{qty(Number(quantity))}</strong>.</>}</p>}
      <label>Ngày {kind === "issue" ? "xuất" : "kiểm kê"}<input type="date" name="occurred_on" required max={today} defaultValue={today} /></label>
      <label>Mã phiếu đối chiếu<input name="external_ref" required maxLength={120} /></label>
      <label>Lý do {kind === "issue" ? "xuất" : "điều chỉnh"}<textarea name="reason" required maxLength={1000} rows={2} /></label>
      <p className="caption">{kind === "count" ? "Nhập số đếm được, không nhập số chênh lệch. Số 0 nghĩa là kho không còn sản phẩm này." : "Chỉ xuất khi tồn kho đủ. Hệ thống kiểm tra lại số dư trước khi ghi sổ."}</p>
    </div><div className="dialog-form-actions"><button type="button" onClick={navigation.close}>Hủy</button><button className="primary" type="submit" disabled={!valid || !position.data || position.loading || !!position.error || !today}>{write.busy ? "Đang ghi sổ…" : "Ghi sổ"}</button></div></fieldset></form>
  </Dialog>;
}
