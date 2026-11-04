import { useEffect, useRef, useState } from "react";
import { api } from "../../services/http";
import { errorLabel } from "../../utils/labels";

export function RunRetry({ id, onCreated, disabled = false, onBusyChange }: {
  id: string; onCreated: (id: string) => void; disabled?: boolean; onBusyChange?: (busy: boolean) => void;
}) {
  const key = useRef(crypto.randomUUID()), sending = useRef(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const [busy, setBusy] = useState(false), [error, setError] = useState<Error>();
  async function retry() {
    if (sending.current || disabled) return;
    sending.current = true; setBusy(true); setError(undefined);
    onBusyChange?.(true);
    try {
      const result = await api<{ run_id: string }>(`/runs/${id}/retry`, {
        method: "POST", headers: { "Idempotency-Key": key.current },
      });
      if (!mounted.current) return;
      window.dispatchEvent(new Event("sigma:refresh"));
      onCreated(result.run_id);
    } catch (reason) { if (mounted.current) setError(reason as Error); }
    finally { sending.current = false; if (mounted.current) { setBusy(false); onBusyChange?.(false); } }
  }
  return <>
    <button className="secondary" disabled={busy || disabled} onClick={retry}>
      {busy ? "Đang gửi…" : "Thử lại với cấu hình hiện tại"}
    </button>
    {error && <p role="alert">{errorLabel(error)}</p>}
  </>;
}
