import { useState, type FormEvent } from "react";
import { Dialog } from "../components/ui/Dialog";
import { WriteError } from "./WriteError";
import { useTradeNavigation } from "../hooks/useTradeNavigation";
import { useOperationWrite, refreshOperations } from "./useOperationWrite";
import type { Product, Supplier, Warehouse } from "./types";

export function CatalogEditor({ kind, row, onClose }: {
  kind: "warehouse" | "product" | "supplier"; row?: Warehouse | Product | Supplier; onClose: () => void;
}) {
  const write = useOperationWrite();
  const [dirty, setDirty] = useState(false);
  const navigation = useTradeNavigation(dirty, write.busy, onClose, false);
  const title = kind === "supplier" ? "Thời gian nhập của nhà cung cấp" : `${row ? "Cập nhật" : "Thêm"} ${kind === "warehouse" ? "kho hàng" : "sản phẩm"}`;
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const fields = new FormData(event.currentTarget);
    let body: Record<string, unknown>, path: string;
    if (kind === "supplier") {
      path = `/suppliers/${row!.id}/settings`;
      body = { lead_time_days: Number(fields.get("lead_time_days")), expected_version: row!.version, reason: fields.get("reason") };
    } else if (kind === "warehouse") {
      path = row ? `/warehouses/${row.id}` : "/warehouses";
      body = { name: fields.get("name"), country: fields.get("country"), ...(row ? { active: fields.get("active") === "true", expected_version: row.version, reason: fields.get("reason") } : { code: fields.get("code") }) };
    } else {
      path = row ? `/products/${row.id}` : "/products";
      body = { name: fields.get("name"), ...(row ? { active: fields.get("active") === "true", expected_version: row.version, reason: fields.get("reason") }
        : { sku: fields.get("sku"), product_type: fields.get("product_type"), carrier: fields.get("carrier"), destination_country: fields.get("destination_country") }) };
    }
    const result = await write.send(path, body, row ? "PATCH" : "POST");
    if (result) { navigation.finish(); refreshOperations(); onClose(); }
  }
  return <Dialog title={title} onClose={navigation.close} busy={write.busy} className="operations-form-dialog">
    <form onSubmit={(event) => void save(event)} onChange={() => setDirty(true)}><fieldset disabled={write.busy}>
      <div className="operations-form-fields"><WriteError error={write.error} />
        {kind === "supplier" ? <><p>Nhà cung cấp: <strong>{String(row?.carrier)}</strong></p>
          <label>Thời gian nhập cho đơn mới (ngày)<input name="lead_time_days" type="number" required min={1} max={365} step={1} defaultValue={Number(row?.lead_time_days ?? 7)} /></label>
          <p className="caption">Áp dụng cho đơn lập sau khi lưu. Đơn đã có giữ ngày dự kiến đã chốt.</p></> : <>
          {kind === "warehouse" && !row && <label>Mã kho<input name="code" required maxLength={40} pattern="[A-Za-z0-9][A-Za-z0-9_\-]*" placeholder="VD: HCM-01" /></label>}
          <label>{kind === "warehouse" ? "Tên kho" : "Tên sản phẩm"}<input name="name" required maxLength={kind === "warehouse" ? 120 : 160} defaultValue={String(row?.name ?? "")} /></label>
          {kind === "warehouse" ? <label>Quốc gia của kho<input name="country" required maxLength={100} defaultValue={String(row?.country ?? "Việt Nam")} /></label> : !row && <>
            <label>Mã SKU<input name="sku" required maxLength={120} /></label>
            <label>Loại sản phẩm<select name="product_type" defaultValue="physical_SIM"><option value="physical_SIM">SIM vật lý</option><option value="eSIM">eSIM</option></select></label>
            <label>Nhà cung cấp / nhà mạng<input name="carrier" required maxLength={100} placeholder="Tên nhà cung cấp chính xác" /></label>
            <label>Quốc gia sử dụng sản phẩm<input name="destination_country" required maxLength={100} /></label>
          </>}
          {row && <label>Trạng thái<select name="active" defaultValue={String(row.active)}><option value="true">Đang hoạt động</option><option value="false">{kind === "warehouse" ? "Đóng kho" : "Ngừng nhập mới"}</option></select></label>}
        </>}
        {row && <label>Lý do thay đổi<textarea name="reason" required maxLength={1000} rows={2} /></label>}
      </div><div className="dialog-form-actions"><button type="button" onClick={navigation.close}>Hủy</button><button className="primary" type="submit">{write.busy ? "Đang lưu…" : "Lưu"}</button></div>
    </fieldset></form>
  </Dialog>;
}
