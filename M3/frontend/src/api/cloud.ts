/** Streamlit Component RPC. Only public aggregate/session operations cross this bridge. */
export const CLOUD = import.meta.env.MODE === "streamlit";
interface RequestMessage {
  id: string;
  path: string;
  method: string;
  body: unknown;
  idempotency?: string;
}
interface Reply {
  ok: boolean;
  status: number;
  data?: unknown;
  csv?: string;
  error?: { code: string; message: string };
}
const pending = new Map<
  string,
  {
    request: RequestMessage;
    resolve: (reply: Reply) => void;
    reject: (error: Error) => void;
  }
>();
let send: (value: unknown) => void = () => {};
let scheduled = false,
  lastSent = "";
let readyResolve: () => void;
let readyReject: (error: Error) => void;
const ready = new Promise<void>((resolve, reject) => {
  readyResolve = resolve;
  readyReject = reject;
});
function flush() {
  if (scheduled) return;
  scheduled = true;
  queueMicrotask(() => {
    scheduled = false;
    const requests = [...pending.values()].map((v) => v.request);
    const signature = requests.map((r) => r.id).join(",");
    if (!requests.length || signature === lastSent) return;
    lastSent = signature;
    send({ requests });
  });
}
export async function initCloud() {
  const { Streamlit } = await import("streamlit-component-lib");
  send = (value) => Streamlit.setComponentValue(value);
  Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, (event: Event) => {
    const args = (event as CustomEvent).detail.args;
    Streamlit.setFrameHeight(Number(args.frame_height) || 900);
    const responses = args.responses ?? {};
    for (const [id, entry] of pending) {
      if (Object.prototype.hasOwnProperty.call(responses, id)) {
        pending.delete(id);
        entry.resolve(responses[id]);
      }
    }
    readyResolve();
  });
  const bootTimer = setTimeout(
    () =>
      readyReject(
        new Error(
          "Chưa kết nối được với máy chủ. Hãy kiểm tra mạng rồi tải lại trang.",
        ),
      ),
    20000,
  );
  Streamlit.setComponentReady();
  try {
    await ready;
  } finally {
    clearTimeout(bootTimer);
  }
}
export async function cloudRequest(
  path: string,
  options: RequestInit = {},
): Promise<Reply> {
  await ready;
  if (options.signal?.aborted)
    throw new DOMException("Request aborted", "AbortError");
  const id = crypto.randomUUID();
  const request: RequestMessage = {
    id,
    path,
    method: options.method ?? "GET",
    body: typeof options.body === "string" ? JSON.parse(options.body) : null,
    idempotency:
      new Headers(options.headers).get("Idempotency-Key") ?? undefined,
  };
  return new Promise((resolve, reject) => {
    const cleanup = () => {
      clearTimeout(timer);
      options.signal?.removeEventListener("abort", abort);
    };
    const abort = () => {
      cleanup();
      pending.delete(id);
      reject(new DOMException("Request aborted", "AbortError"));
      flush();
    };
    const finish = (reply: Reply) => {
      cleanup();
      resolve(reply);
    };
    const timer = setTimeout(
      () => {
        cleanup();
        pending.delete(id);
        flush();
        reject(
          new Error(
            request.method === "GET"
              ? "Kết nối quá thời gian. Hãy kiểm tra mạng và bấm Thử tải lại."
              : "Chưa nhận được phản hồi. Thao tác có thể đã được xử lý; hãy làm mới và kiểm tra danh sách trước khi gửi lại.",
          ),
        );
      },
      request.method === "GET" ? 30000 : 90000,
    );
    pending.set(id, { request, resolve: finish, reject });
    options.signal?.addEventListener("abort", abort, { once: true });
    flush();
  });
}
export async function prepareCloudCsv(path: string, signal?: AbortSignal) {
  const reply = await cloudRequest(path, { signal });
  if (!reply.ok || reply.csv === undefined)
    throw new Error(reply.error?.message ?? "Không thể xuất CSV");
  return URL.createObjectURL(
    new Blob(["\ufeff", reply.csv], { type: "text/csv;charset=utf-8" }),
  );
}
