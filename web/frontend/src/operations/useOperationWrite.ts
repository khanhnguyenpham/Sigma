import { useRef, useState } from "react";
import { api, ApiError } from "../services/http";

export function useOperationWrite(base = "/operations") {
  const [busy, setBusy] = useState(false), [error, setError] = useState<Error>();
  const retry = useRef({ body: "", key: "" });
  const inFlight = useRef(false);
  async function send<T>(path: string, body: unknown, method = "POST"): Promise<T | undefined> {
    if (inFlight.current) return;
    inFlight.current = true;
    const serialized = JSON.stringify(body), signature = `${method}:${path}:${serialized}`;
    if (retry.current.body !== signature) retry.current = { body: signature, key: crypto.randomUUID() };
    setBusy(true); setError(undefined);
    try { return await api<T>(base + path, { method, headers: { "Content-Type": "application/json", "Idempotency-Key": retry.current.key }, body: serialized }); }
    catch (failure) {
      setError(failure instanceof ApiError && failure.code === "invalid_input" ? new Error("Vui lòng kiểm tra các trường bắt buộc và số lượng trước khi lưu.")
        : failure instanceof ApiError && failure.code === "version_conflict" ? new Error("Dữ liệu đã được người khác cập nhật. Giữ lại thông tin cần thiết, đóng form rồi mở lại để đối chiếu trước khi ghi sổ.") : failure as Error);
      return undefined;
    } finally { inFlight.current = false; setBusy(false); }
  }
  return { busy, error, send };
}

export function refreshOperations() { window.dispatchEvent(new Event("sigma:refresh")); }
