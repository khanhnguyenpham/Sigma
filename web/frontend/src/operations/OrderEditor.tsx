import { useState, type FormEvent } from "react";
import { Dialog } from "../components/ui/Dialog";
import { WriteError } from "./WriteError";
import { useTradeNavigation } from "../hooks/useTradeNavigation";
import { ProductPicker } from "./ProductPicker";
import { refreshOperations, useOperationWrite } from "./useOperationWrite";
import { qty, type Order, type Product, type Supplier, type Warehouse } from "./types";

interface DraftLine { item_id: number; warehouse_id: number; quantity: number; name: string; sku: string }
export function OrderEditor({ order: suppliedOrder, suppliers, warehouses, today, onClose, onSaved }: {
  order?: Order; suppliers: Supplier[]; warehouses: Warehouse[]; today: string; onClose: () => void; onSaved: (order: Order) => void;
}) {
  const [order] = useState(suppliedOrder);
  const [supplier, setSupplier] = useState(order?.supplier_id ?? 0), [warehouse, setWarehouse] = useState(warehouses[0]?.id ?? 0);
  const [lines, setLines] = useState<DraftLine[]>(order?.lines.map((line) => ({ item_id: line.item_id, warehouse_id: line.warehouse_id, quantity: line.ordered_qty, name: line.name, sku: line.sku })) ?? []);
  const [dirty, setDirty] = useState(false), [validation, setValidation] = useState("");
  const write = useOperationWrite(), navigation = useTradeNavigation(dirty, write.busy, onClose, false);
  function add(product: Product) {
    if (!warehouse) { setValidation("Chọn kho nhận trước khi thêm sản phẩm."); return; }
    if (lines.some((line) => line.item_id === product.id && line.warehouse_id === warehouse)) { setValidation("Sản phẩm này đã có trong kho nhận được chọn. Hãy sửa số lượng ở dòng đã thêm."); return; }
    setLines([...lines, { item_id: product.id, warehouse_id: warehouse, quantity: 1, name: product.name, sku: product.sku }]); setDirty(true); setValidation("");
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!lines.length || lines.some((line) => !Number.isSafeInteger(line.quantity) || line.quantity <= 0) || !Number.isSafeInteger(lines.reduce((total, line) => total + line.quantity, 0))) { setValidation("Thêm ít nhất một sản phẩm và nhập số lượng nguyên dương trong giới hạn hỗ trợ."); return; }
    const fields = new FormData(event.currentTarget);
    const body = { supplier_id: supplier, ordered_on: fields.get("ordered_on"), note: fields.get("note"), lines: lines.map(({ item_id, warehouse_id, quantity }) => ({ item_id, warehouse_id, quantity })), ...(order ? { expected_version: order.version } : {}) };
    const saved = await write.send<Order>(order ? `/orders/${order.id}` : "/orders", body, order ? "PATCH" : "POST");
    if (saved) { navigation.finish(); refreshOperations(); onSaved(saved); }
  }
  return <Dialog title={order ? `Sửa đơn ${order.number}` : "Tạo đơn nhập hàng"} onClose={navigation.close} busy={write.busy} className="operations-form-dialog wide">
    <form onSubmit={(event) => void save(event)} onChange={() => setDirty(true)}><fieldset disabled={write.busy}>
      <div className="operations-form-fields"><WriteError error={write.error} />{validation && <p role="alert" className="notice error">{validation}</p>}
        <div className="ops-form-grid"><label>Nhà cung cấp<select aria-label="Nhà cung cấp" required value={supplier || ""} disabled={lines.length > 0} onChange={(event) => setSupplier(Number(event.target.value))}><option value="">Chọn nhà cung cấp</option>{suppliers.map((row) => <option key={row.id} value={row.id}>{row.carrier} · {row.lead_time_days} ngày</option>)}</select></label>
          <label>Ngày đặt<input name="ordered_on" type="date" required max={today} defaultValue={order?.ordered_on ?? today} /></label></div>
        <p className="caption">Lưu nháp chưa tăng tồn kho. Xác nhận đơn trước khi nhận hàng. Muốn đổi nhà cung cấp, xóa các dòng đã thêm.</p>
        <label>Kho nhận cho sản phẩm thêm tiếp<select value={warehouse || ""} required onChange={(event) => setWarehouse(Number(event.target.value))}><option value="">Chọn kho nhận</option>{warehouses.map((row) => <option key={row.id} value={row.id}>{row.code} · {row.name}</option>)}</select></label>
        <ProductPicker supplierId={supplier} onPick={add} />
        <h3>Sản phẩm trong đơn ({lines.length})</h3><div className="ops-draft-lines">{lines.length === 0 && <p>Chưa thêm sản phẩm.</p>}{lines.map((line, index) => <div className="ops-draft-line" key={`${line.item_id}:${line.warehouse_id}`}><span><strong>{line.sku}</strong><small>{line.name} · {warehouses.find((row) => row.id === line.warehouse_id)?.name ?? `Kho ${line.warehouse_id}`}</small></span>
          <label>Số lượng<input type="number" aria-label={`Số lượng ${line.sku}`} required min={1} max={Number.MAX_SAFE_INTEGER} step={1} value={line.quantity || ""} onChange={(event) => setLines(lines.map((row, position) => position === index ? { ...row, quantity: Number(event.target.value) } : row))} /></label>
          <button type="button" aria-label={`Xóa ${line.sku}`} onClick={() => { setLines(lines.filter((_, position) => position !== index)); setDirty(true); }}>Xóa</button></div>)}</div>
        <p>Tổng số lượng: <strong>{qty(lines.reduce((total, line) => total + line.quantity, 0))}</strong></p>
        <label>Ghi chú nội bộ<textarea name="note" rows={2} maxLength={1000} defaultValue={order?.note ?? ""} /></label>
      </div><div className="dialog-form-actions"><button type="button" onClick={navigation.close}>Hủy</button><button className="primary" type="submit" disabled={!lines.length || !supplier || !today}>{write.busy ? "Đang lưu…" : "Lưu nháp"}</button></div>
    </fieldset></form>
  </Dialog>;
}
