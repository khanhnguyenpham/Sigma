import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../services/http";
import type { Row } from "../types/api";

export function useTradeWrite(options: { draft: Row; previewPath: string; savePath: string; saveDraft?: (draft: Row) => Row; reload: (saved?: Row) => Promise<unknown>; onSaved: (saved: Row) => void }) {
  const serialized = JSON.stringify(options.draft), current = useRef(options), mounted = useRef(true);
  current.current = options;
  const payloadKey = useRef(serialized); payloadKey.current = serialized;
  const [preview, setPreview] = useState<{ key: string; data: Row; page: number }>();
  const [previewing, setPreviewing] = useState(false), [saving, setSaving] = useState(false), [error, setError] = useState<Error>();
  const [conflict, setConflict] = useState(false), [uncertain, setUncertain] = useState(false), [saved, setSaved] = useState<Row>();
  const sending = useRef(false), pending = useRef<AbortController | undefined>(undefined);
  useEffect(() => { pending.current?.abort(); setPreview(undefined); }, [serialized]);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; pending.current?.abort(); }; }, []);
  async function showPreview(page = 1) {
    if (sending.current || saved || uncertain) return;
    pending.current?.abort(); const controller = new AbortController(); pending.current = controller;
    const key = serialized; setPreview(undefined); setPreviewing(true); setError(undefined); setConflict(false);
    try {
      const data = await api<Row>(`${current.current.previewPath}?page=${page}&page_size=50`, { method:"POST",headers:{"Content-Type":"application/json"},body:key,signal:controller.signal });
      if (mounted.current && payloadKey.current === key && !controller.signal.aborted) setPreview({ key, data, page });
    } catch (e) { if (mounted.current && !controller.signal.aborted) {setError(e as Error);setConflict(e instanceof ApiError && e.status===409);} }
    finally { if (mounted.current && pending.current === controller) setPreviewing(false); }
  }
  async function reload() {
    if (sending.current) return;
    setSaving(true); setError(undefined);
    try {
      await current.current.reload(saved);
      if (!mounted.current) return;
      setConflict(false); setPreview(undefined);
      if (saved) current.current.onSaved(saved);
    } catch (e) { if (mounted.current) setError(e as Error); }
    finally { if (mounted.current) setSaving(false); }
  }
  async function save() {
    if (sending.current || !preview || preview.key !== serialized || conflict || saved || uncertain) return;
    sending.current = true; setSaving(true); setError(undefined);
    try {
      const opts = current.current, draft = opts.saveDraft ? opts.saveDraft(opts.draft) : opts.draft;
      const result = await api<Row>(opts.savePath, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({...draft,preview_fingerprint:preview.data.preview_fingerprint})});
      if (!mounted.current) return;
      setSaved(result);
      await opts.reload(result);
      if (mounted.current) opts.onSaved(result);
    } catch (e) {
      if (!mounted.current) return;
      setError(e as Error); setPreview(undefined);
      setConflict(e instanceof ApiError && e.status === 409);
      setUncertain(!(e instanceof ApiError) || e.code === "request_timeout" || e.status >= 500);
    } finally { sending.current = false; if (mounted.current) setSaving(false); }
  }
  return { preview:preview?.key === serialized ? preview.data : undefined, page:preview?.page ?? 1, previewing, saving, busy:previewing || saving, error, conflict, uncertain, saved, showPreview, save, reload };
}
