import { useState, type FormEvent } from "react";
import { Dialog } from "../components/ui/Dialog";
import { State } from "../components/ui/State";
import { ProductPolicyForm } from "../components/products/ProductPolicyForm";
import { useResource } from "../hooks/useResource";
import { WriteError } from "./WriteError";
import { useOperationWrite, refreshOperations } from "./useOperationWrite";
import type { Page, Row } from "../types/api";
import type { Product, Supplier } from "./types";

/** Lead time stays a supplier setting (shared by its products); lot, ROP floor and safety days are versioned per product. */
export function ProductPolicyDialog({ product, supplier, onClose }: { product: Product; supplier?: Supplier; onClose: () => void }) {
  const [reload, setReload] = useState(0);
  // Rows come newest version first, so the first one is the version a new policy must follow.
  const latest = useResource<Page<Row>>(`/supplier-item-policies?item_id=${product.id}&page_size=1&_=${reload}`);
  const write = useOperationWrite();
  const [saved, setSaved] = useState("");
  async function saveLead(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const fields = new FormData(event.currentTarget);
    const result = await write.send(`/suppliers/${supplier!.id}/settings`, { lead_time_days: Number(fields.get("lead_time_days")),
      expected_version: supplier!.version, reason: fields.get("reason") }, "PATCH");
    if (result) { setSaved("Đã lưu thời gian nhập."); refreshOperations(); }
  }
  const policy = latest.data?.items[0] ?? null;
  return <Dialog title={`Chính sách nhập · ${product.name}`} onClose={onClose} busy={write.busy} className="operations-form-dialog wide">
    <div className="operations-form-fields">
      <section aria-label="Thời gian nhập"><h3>Thời gian nhập</h3>
        {supplier ? <form onSubmit={(event) => void saveLead(event)}><fieldset disabled={write.busy}>
          <WriteError error={write.error} />
          <label>Thời gian nhập (ngày)<input name="lead_time_days" type="number" required min={1} max={365} step={1} defaultValue={supplier.lead_time_days} /></label>
          <p className="caption">Thiết lập theo nhà cung cấp <strong>{supplier.carrier}</strong>, áp dụng cho {supplier.product_count ?? 0} sản phẩm của nhà cung cấp này. Đơn nhập đã lập giữ ngày đã chốt.</p>
          <label>Lý do thay đổi<input name="reason" required maxLength={1000} /></label>
          <div className="form-actions">{saved && <span className="caption" role="status">{saved}</span>}<button className="primary">{write.busy ? "Đang lưu…" : "Lưu thời gian nhập"}</button></div>
        </fieldset></form> : <p className="notice">Chưa tải được nhà cung cấp của sản phẩm.</p>}
      </section>
      <section aria-label="Lượng nhập và ngưỡng"><h3>Lượng nhập và ngưỡng</h3>
        <State loading={latest.loading && !latest.data} error={latest.error} />
        {latest.data && <ProductPolicyForm key={String(policy?.version ?? 0)} product={{ id: product.id, supplier_id: product.supplier_id, policy, lead_time_days: supplier?.lead_time_days }}
          onSaved={() => { setReload((value) => value + 1); setSaved("Đã lưu chính sách nhập."); refreshOperations(); }} onReload={() => setReload((value) => value + 1)} />}
      </section>
    </div>
  </Dialog>;
}
