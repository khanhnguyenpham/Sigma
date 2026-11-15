import { useRef, useState, type FormEvent } from "react";
import { Dialog } from "../components/ui/Dialog";
import { WriteError } from "./WriteError";
import { useTradeNavigation } from "../hooks/useTradeNavigation";
import { refreshOperations, useOperationWrite } from "./useOperationWrite";
import { qty, type Order } from "./types";
import { ReceiptQr } from "./ReceiptQr";

export function ReceiptEditor({ order: suppliedOrder, today, onClose, onSaved }: { order: Order; today: string; onClose: () => void; onSaved: () => void }) {
  const [order] = useState(suppliedOrder);
  const formRef = useRef<HTMLFormElement>(null);
  const [qrBusy,setQrBusy] = useState(false);
  const pending = order.lines.filter((line) => line.remaining_qty > 0);
  const [quantities, setQuantities] = useState<Record<number, number>>(() => Object.fromEntries(pending.map((line) => [line.id, line.remaining_qty])));
  const [dirty, setDirty] = useState(false), [validation, setValidation] = useState("");
  const write = useOperationWrite(), navigation = useTradeNavigation(dirty, write.busy || qrBusy, onClose, false);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if(qrBusy)return;
    if (pending.some((line) => !Number.isSafeInteger(quantities[line.id]) || quantities[line.id] < 0 || quantities[line.id] > line.remaining_qty)) { setValidation("Số nhận phải là số nguyên, từ 0 đến số lượng còn thiếu."); return; }
    const lines = pending.filter((line) => quantities[line.id] > 0).map((line) => ({ order_line_id: line.id, quantity: quantities[line.id] }));
    if (!lines.length) { setValidation("Nhập ít nhất một sản phẩm đã nhận. Để 0 với sản phẩm chưa về."); return; }
    const fields = new FormData(event.currentTarget);
    const result = await write.send(`/orders/${order.id}/receipts`, { expected_version: order.version, occurred_on: fields.get("occurred_on"), external_ref: fields.get("external_ref"), reason: fields.get("reason"), lines });
    if (result) { navigation.finish(); refreshOperations(); onSaved(); }
  }
  return <Dialog title={`Nhận hàng · ${order.number}`} onClose={navigation.close} busy={write.busy || qrBusy} className="operations-form-dialog">
    <form ref={formRef} onSubmit={(event) => void save(event)} onChange={() => setDirty(true)}><fieldset disabled={write.busy || qrBusy}><div className="operations-form-fields">
      <WriteError error={write.error} />{validation && <p role="alert" className="notice error">{validation}</p>}
      <p>Chỉ ghi số lượng thực nhận. Nhận thiếu sẽ giữ phần còn lại ở trạng thái chờ.</p>
      <label>Ngày nhận thực tế<input type="date" name="occurred_on" required min={order.ordered_on} max={today} defaultValue={today} /></label>
      <label>Mã phiếu giao hàng<input name="external_ref" required maxLength={120} placeholder="Mã trên phiếu của nhà cung cấp" /></label>
      {pending.some(line=>line.product_type==='physical_SIM') && <ReceiptQr orderId={order.id} version={order.version} onBusy={setQrBusy} getBody={()=>{
        if(!formRef.current?.reportValidity())return undefined;
        const fields=new FormData(formRef.current);
        return {expected_version:order.version,occurred_on:fields.get('occurred_on'),external_ref:fields.get('external_ref'),lines:pending.filter(line=>quantities[line.id]>0).map(line=>({order_line_id:line.id,quantity:quantities[line.id]}))};
      }} onApply={result=>{
        setQuantities(Object.fromEntries(pending.map(line=>[line.id,result.lines.find(row=>row.order_line_id===line.id)?.quantity??0])));
        const field=formRef.current?.elements.namedItem('external_ref') as HTMLInputElement|null;if(field)field.value=result.external_ref;
        setDirty(true);setValidation('');
      }}/>}
      {pending.map((line) => <label key={line.id}>{line.sku} · {line.warehouse}<small>Còn thiếu {qty(line.remaining_qty)} · Đã nhận {qty(line.received_qty)}</small>
        <input type="number" aria-label={`Thực nhận ${line.sku}`} required min={0} max={line.remaining_qty} step={1} value={quantities[line.id]} onChange={(event) => setQuantities({ ...quantities, [line.id]: Number(event.target.value) })} /></label>)}
      <label>Ghi chú nhận hàng<textarea name="reason" rows={2} maxLength={1000} /></label>
      <p className="caption">Ghi sổ sẽ tăng tồn kho ngay và lưu chứng từ. Không sửa hoặc xóa trực tiếp phiếu đã ghi.</p>
    </div><div className="dialog-form-actions"><button type="button" onClick={navigation.close}>Hủy</button><button type="submit" className="primary" disabled={!today}>{write.busy ? "Đang ghi sổ…" : "Ghi nhận nhập kho"}</button></div></fieldset></form>
  </Dialog>;
}
