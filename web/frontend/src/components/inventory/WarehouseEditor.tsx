import { useRef, useState } from "react";
import type { Row } from "../../types/api";
import { api } from "../../services/http";
import { useResource } from "../../hooks/useResource";
import { useDialogFocus } from "../../hooks/useDialogFocus";
import { State } from "../ui/State";
import { errorLabel } from "../../utils/labels";

export function WarehouseEditor({ id, onClose }: { id: string; onClose: () => void }) {
  const data = useResource<Row>(`/warehouses/${id}`);
  const [busy, setBusy] = useState(false), [error, setError] = useState<Error>();
  const sending = useRef(false);
  useDialogFocus(true, onClose);
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (sending.current || !data.data || !event.currentTarget.reportValidity()) return;
    const form = new FormData(event.currentTarget);
    sending.current = true; setBusy(true); setError(undefined);
    try {
      await api(`/warehouses/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ city: String(form.get("city")), expected_version: data.data.version }) });
      window.dispatchEvent(new Event("sigma:refresh")); onClose();
    } catch (e) { setError(e as Error); }
    finally { sending.current = false; setBusy(false); }
  }
  return <div className="modal-shade"><section className="modal" role="dialog" aria-modal="true" aria-labelledby="warehouse-edit-title">
    <button className="close" aria-label="Đóng chỉnh sửa kho" onClick={onClose}>×</button><h2 id="warehouse-edit-title">Chỉnh sửa kho</h2>
    <State loading={data.loading} error={data.error} />
    {data.data && <form onSubmit={save}><label>Tên kho<input name="city" defaultValue={String(data.data.city)} required maxLength={100} /></label>
      <p className="caption">{String(data.data.destination_country)} · Nhà mạng {String(data.data.carrier)}</p>
      {error && <div className="notice error" role="alert">{errorLabel(error)}</div>}
      <div className="form-actions"><button type="button" onClick={onClose}>Hủy</button><button className="primary" disabled={busy}>{busy ? "Đang lưu…" : "Lưu thông tin kho"}</button></div>
    </form>}
  </section></div>;
}
