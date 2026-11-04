import { API_PREFIX, READ_TIMEOUT_MS, WRITE_TIMEOUT_MS } from "../config/http";
import type { Page, Row } from "../types/api";

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
      const response = await fetch(API_PREFIX + path, { ...options, signal: controller.signal });
      const data = await response.json();
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
