import { useRef, useState } from "react";
import type { Row } from "../../types/api";
import { api } from "../../services/http";
import { errorLabel } from "../../utils/labels";
import { POLICY_DEFAULTS } from "../../config/policy";
import { PolicyFields } from "../configuration/PolicyFields";

export function ProductPolicyForm({ product, onSaved, onReload }: { product: Row; onSaved: () => void; onReload: () => void }) {
  const policy = product.policy as Row | null;
  const [values, setValues] = useState<Row>({ configured_rop_floor: 0, safety_days: 2, ...POLICY_DEFAULTS, ...policy });
  const [busy, setBusy] = useState(false), [error, setError] = useState<Error>();
  const sending = useRef(false);
  const next = new Date(String(policy?.effective_from ?? "2000-01-01") + "T00:00:00Z");
  next.setUTCDate(next.getUTCDate() + 1);
  const earliest = [new Date().toISOString().slice(0, 10), next.toISOString().slice(0, 10)].sort().at(-1)!;
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending.current || !event.currentTarget.reportValidity()) return;
    const form = new FormData(event.currentTarget);
    const body: Row = { item_id: Number(product.id), supplier_id: Number(product.supplier_id),
      expected_version: Number(policy?.version ?? 0), effective_from: String(form.get("effective_from")) };
    for (const key of ["configured_rop_floor", "fixed_order_qty", "safety_days", "warning_horizon_days"])
      body[key] = Number(form.get(key));
    sending.current = true; setBusy(true); setError(undefined);
    try {
      await api("/supplier-item-policies", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      onSaved();
    } catch (e) { setError(e as Error); }
    finally { sending.current = false; setBusy(false); }
  }
  return <form className="product-policy-form" onSubmit={save} aria-label="Cấu hình nhập hàng sản phẩm">
    <fieldset disabled={busy}>
      <PolicyFields policy={values} onChange={(key, value) => setValues((previous) => ({ ...previous, [key]: value }))} />
      <label>Áp dụng từ ngày<input name="effective_from" type="date" required min={earliest} defaultValue={earliest} /></label>
      <p className="caption">Thời gian nhập hàng: 7 ngày. Kiểm tra bổ sung hằng ngày. Cấu hình áp dụng cho các kế hoạch được tính từ ngày hiệu lực.</p>
      {product.supplier_id == null && <p className="notice error" role="alert">Chưa xác định được nhà cung cấp của sản phẩm.</p>}
      {error && <div className="notice error" role="alert">{errorLabel(error)}<button type="button" className="text-button" onClick={onReload}>Tải lại cấu hình</button></div>}
      <div className="form-actions"><button className="primary" disabled={busy || product.supplier_id == null}>{busy ? "Đang lưu…" : "Lưu cấu hình sản phẩm"}</button></div>
    </fieldset>
  </form>;
}
