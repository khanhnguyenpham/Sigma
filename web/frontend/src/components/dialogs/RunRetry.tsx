import { useRef, useState } from "react";
import { api } from "../../services/http";
import { errorLabel } from "../../utils/labels";

export function RunRetry({ id, onCreated }: { id: string; onCreated: (id: string) => void }) {
  const key = useRef(crypto.randomUUID()), sending = useRef(false);
  const [busy, setBusy] = useState(false), [error, setError] = useState<Error>();
  async function retry() {
    if (sending.current) return;
    sending.current = true; setBusy(true); setError(undefined);
    try {
      const result = await api<{ run_id: string }>(`/runs/${id}/retry`, {
        method: "POST", headers: { "Idempotency-Key": key.current },
      });
      window.dispatchEvent(new Event("sigma:refresh"));
      onCreated(result.run_id);
    } catch (reason) { setError(reason as Error); }
    finally { sending.current = false; setBusy(false); }
  }
  return <>
    <button className="secondary" disabled={busy} onClick={retry}>
      {busy ? "Đang gửi…" : "Thử lại với cấu hình hiện tại"}
    </button>
    {error && <p role="alert">{errorLabel(error)}</p>}
  </>;
}
