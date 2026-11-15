import { useState } from "react";
import { useResource } from "../hooks/useResource";
import { Table } from "../components/ui/Table";
import { Dialog } from "../components/ui/Dialog";
import { State } from "../components/ui/State";
import { WriteError } from "./WriteError";
import { refreshOperations, useOperationWrite } from "./useOperationWrite";
import { ReceiptEditor } from "./ReceiptEditor";
import { OrderEditor } from "./OrderEditor";
import { qty, ORDER_STATUS, type Order, type Supplier, type Warehouse } from "./types";

export function OrderDetail({ id, today, suppliers, warehouses, onBack }: { id: string; today: string; suppliers: Supplier[]; warehouses: Warehouse[]; onBack: () => void }) {
  const result = useResource<Order>(`/operations/orders/${id}`, true);
  const [action, setAction] = useState<"receipt" | "edit" | "confirm" | "cancel">();
  const write = useOperationWrite(), order = result.data;
  const actionable = order?.status === "draft" || order?.status === "ordered" || order?.status === "partially_received";
  return <section className="panel ops-order-detail"><div className="ops-section-heading"><button onClick={onBack}>← Danh sách đơn</button><span>Chi tiết đơn nhập</span></div>
    <State loading={result.loading} error={result.error} />
    {order && <><div className="ops-section-heading"><div><h2>{order.number}</h2><span className={`ops-status ${order.status}`}>{ORDER_STATUS[order.status]}</span></div>
      <div className="ops-actions">{order.status === "draft" && <><button onClick={() => setAction("edit")}>Sửa nháp</button><button className="primary" onClick={() => setAction("confirm")}>Xác nhận đặt hàng</button></>}
        {["ordered", "partially_received"].includes(order.status) && <button className="primary" disabled={!today} onClick={() => setAction("receipt")}>Nhận hàng</button>}
        {actionable && <button onClick={() => setAction("cancel")}>{order.status === "partially_received" ? "Hủy phần chưa nhận" : "Hủy đơn"}</button>}</div></div>
      <dl className="ops-detail-grid"><div><dt>Nhà cung cấp</dt><dd>{order.carrier}</dd></div><div><dt>Ngày đặt</dt><dd>{order.ordered_on}</dd></div><div><dt>Dự kiến nhận</dt><dd>{order.eta}</dd></div><div><dt>Thời gian nhập đã chốt</dt><dd>{order.lead_time_days} ngày</dd></div></dl>
      {order.note && <p>Ghi chú: {order.note}</p>}
      <Table rows={order.lines} stickyFirstColumn columns={[{ key: "sku", label: "Mã sản phẩm" }, { key: "name", label: "Tên sản phẩm" }, { key: "warehouse", label: "Kho nhận" }, { key: "ordered_qty", label: "Đã đặt", render: qty }, { key: "received_qty", label: "Đã nhận", render: qty }, { key: "remaining_qty", label: order.status === "cancelled" ? "Chưa nhận (đã hủy)" : "Còn thiếu", render: qty }]} />
      <p className="caption">Ngày dự kiến nhận được lưu theo nhà cung cấp lúc lập đơn. Tồn kho chỉ tăng khi phiếu nhận hàng được ghi sổ.</p>
      {action === "edit" && <OrderEditor order={order} suppliers={suppliers} warehouses={warehouses} today={today} onClose={() => setAction(undefined)} onSaved={() => setAction(undefined)} />}
      {action === "receipt" && <ReceiptEditor order={order} today={today} onClose={() => setAction(undefined)} onSaved={() => setAction(undefined)} />}
      {(action === "confirm" || action === "cancel") && <Dialog title={action === "confirm" ? "Xác nhận đặt hàng" : "Hủy đơn / phần chưa nhận"} onClose={() => setAction(undefined)} busy={write.busy} className="operations-form-dialog">
        <form onSubmit={(event) => { event.preventDefault(); const reason = new FormData(event.currentTarget).get("reason") ?? ""; void write.send(`/orders/${order.id}/${action}`, { expected_version: order.version, reason }).then((saved) => { if (saved) { setAction(undefined); refreshOperations(); } }); }}><fieldset disabled={write.busy}><div className="operations-form-fields"><WriteError error={write.error} />
          <p>{action === "confirm" ? "Đơn sẽ chuyển sang chờ nhận hàng. Sau khi xác nhận, bạn không sửa các dòng của đơn." : "Chỉ hủy số lượng chưa nhận. Các phiếu đã ghi sổ và tồn đã nhận được giữ nguyên."}</p>
          <label>{action === "cancel" ? "Lý do hủy" : "Ghi chú xác nhận"}<textarea name="reason" required={action === "cancel"} maxLength={1000} rows={3} /></label>
        </div><div className="dialog-form-actions"><button type="button" onClick={() => setAction(undefined)}>Quay lại</button><button className="primary" type="submit">{write.busy ? "Đang xử lý…" : action === "confirm" ? "Xác nhận" : "Xác nhận hủy"}</button></div></fieldset></form>
      </Dialog>}
    </>}
  </section>;
}
