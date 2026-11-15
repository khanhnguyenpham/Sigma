import { API_PREFIX, READ_TIMEOUT_MS, WRITE_TIMEOUT_MS } from "../config/http";
import type { Page, Row } from "../types/api";

let csrfToken = "";
export function setCsrfToken(value: string) { csrfToken = value; }

export async function apiAllPages<T = Row>(path: string, options: RequestInit = {}): Promise<Page<T>> {
  const [pathname, search] = path.split("?");
  const params = new URLSearchParams(search);
  params.set("page_size", "100");
  const items: T[] = [];
  let first: Page<T> | undefined;
  for (let page = 1; ; page++) {
    params.set("page", String(page));
    const result = await api<Page<T>>(`${pathname}?${params}`, options);
    first ??= result;
    items.push(...result.items);
    if (items.length >= result.total || !result.items.length) return { ...first, items, page: 1, page_size: items.length };
  }
}

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
    public details?: { retry_after_seconds?: number; fields?: { location: (string | number)[]; type: string }[] },
  ) {
    super(message);
  }
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (options.signal?.aborted) throw new DOMException("Aborted", "AbortError");
  options.signal?.addEventListener("abort", abort, { once: true });
  let expired = false;
  const timer = setTimeout(() => {
    expired = true;
    controller.abort();
  }, ["GET", "HEAD"].includes((options.method ?? "GET").toUpperCase()) ? READ_TIMEOUT_MS : WRITE_TIMEOUT_MS);
  let rejectAbort: () => void = () => {};
  const aborted = new Promise<never>((_, reject) => {
    rejectAbort = () => reject(expired
      ? new ApiError("request_timeout", "Máy chủ phản hồi quá lâu. Hãy thử lại.", 408)
      : new DOMException("Aborted", "AbortError"));
    controller.signal.addEventListener("abort", rejectAbort, { once: true });
  });
  try {
    return await Promise.race([aborted, (async () => {
      const headers = new Headers(options.headers);
      if (csrfToken && !["GET", "HEAD", "OPTIONS"].includes((options.method ?? "GET").toUpperCase())) headers.set("X-CSRF-Token", csrfToken);
      const response = await fetch(API_PREFIX + path, { ...options, credentials: "include", headers, signal: controller.signal });
      if (response.status === 401 && !path.startsWith("/auth/")) window.dispatchEvent(new Event("sigma:unauthorized"));
      let data;
      try { data = await response.json(); }
      catch {
        throw new ApiError(response.ok ? "invalid_response" : "server_error",
          response.ok ? "Không đọc được dữ liệu trả về. Vui lòng thử lại."
            : "Hệ thống đang gặp sự cố. Vui lòng thử lại sau.", response.ok ? 502 : response.status);
      }
      if (!response.ok) throw new ApiError(
        data.error?.code ?? "network_error",
        data.error?.message ?? "Không thể tải dữ liệu",
        response.status,
        data.error?.details,
      );
      return data as T;
    })()]);
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener("abort", abort);
    controller.signal.removeEventListener("abort", rejectAbort);
  }
}
