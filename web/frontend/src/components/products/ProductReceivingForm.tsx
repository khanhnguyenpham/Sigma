import { useEffect, useRef, useState } from "react";
import type { Row } from "../../types/api";
import { api, apiAllPages, ApiError } from "../../services/http";
import { errorLabel } from "../../utils/labels";
import { warehouseName } from "../../utils/warehouse";
import { State } from "../ui/State";

export function ProductReceivingForm({ product, onSaved, onReload }: {
  product: Row; onSaved: () => void; onReload: () => void;
}) {
  const [base] = useState(() => ({ warehouseId: String(product.receiving_warehouse_id ?? product.warehouse_id),
    version: Number(product.receiving_version ?? 0) }));
  const original = base.warehouseId;
  const [warehouseId, setWarehouseId] = useState(original);
  const [warehouses, setWarehouses] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false), [optionsError, setOptionsError] = useState<Error>();
  const [revision, setRevision] = useState(0), [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error>(), [reloadRequired, setReloadRequired] = useState(false);
  const sending = useRef(false), pending = useRef<AbortController | undefined>(undefined);
  const ready = product.receiving_schema_ready === true;
  useEffect(() => () => pending.current?.abort(), []);
  useEffect(() => {
    if (!ready) return;
    const controller = new AbortController();
    setLoading(true); setOptionsError(undefined);
    apiAllPages("/warehouses", { signal: controller.signal })
      .then((result) => { if (!controller.signal.aborted) setWarehouses(result.items); })
      .catch((reason) => { if (!controller.signal.aborted) setOptionsError(reason as Error); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [ready, revision]);
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending.current || !ready || loading || optionsError || reloadRequired || !event.currentTarget.reportValidity()) return;
    const controller = new AbortController(); pending.current = controller;
    sending.current = true; setBusy(true); setError(undefined);
    try {
      await api(`/products/${product.id}/receiving-warehouse`, {
        method: "PATCH", headers: { "Content-Type": "application/json" }, signal: controller.signal,
        body: JSON.stringify({ receiving_warehouse_id: Number(warehouseId), expected_version: base.version }),
      });
      if (!controller.signal.aborted) onSaved();
    } catch (reason) {
      if (!controller.signal.aborted) {
        setError(reason as Error);
        setReloadRequired(!(reason instanceof ApiError) || reason.status === 409 || reason.status >= 500 || reason.code === "request_timeout");
      }
    } finally { sending.current = false; if (!controller.signal.aborted) setBusy(false); }
  }
  const current = (product.receiving_warehouse ?? product.warehouse) as Row;
  const options = warehouses.some((w) => String(w.id) === original) ? warehouses : [current, ...warehouses].filter(Boolean);
  return <form className="product-receiving-form" onSubmit={save} aria-label="Kho nhận hàng mặc định của sản phẩm">
    <State loading={loading} error={optionsError} />
    {optionsError && <button type="button" onClick={() => setRevision((v) => v + 1)}>Tải lại danh sách kho</button>}
    {!ready && <p className="notice" role="status">Kho nhận hiện theo kho sản phẩm. Cần nâng cấp dữ liệu để lưu lựa chọn riêng.</p>}
    <fieldset disabled={busy || !ready || loading || !!optionsError}>
      <label>Kho nhận hàng mặc định
        <select required value={warehouseId} onChange={(event) => setWarehouseId(event.target.value)}>
          {options.map((w) => <option key={String(w.id)} value={String(w.id)}>{warehouseName(w)} · {String(w.destination_country)}</option>)}
        </select>
      </label>
      {product.receiving_source === "inherited" && <p className="caption">Đang kế thừa kho sản phẩm.</p>}
      <p className="caption">Kịch bản tự dùng kho này cho lượt chạy mới. Lưu không chuyển tồn hoặc đổi kho của lô đã chốt.</p>
      {error && <div className="notice error" role="alert">{errorLabel(error)}<button type="button" className="text-button" onClick={onReload}>Tải lại kho đã lưu</button></div>}
      <button className="primary" disabled={warehouseId === original || reloadRequired}>{busy ? "Đang lưu…" : "Lưu kho nhận"}</button>
    </fieldset>
  </form>;
}
