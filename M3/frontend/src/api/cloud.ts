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
const ready = new Promise<void>((resolve) => {
  readyResolve = resolve;
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
  Streamlit.setComponentReady();
  await ready;
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
    const abort = () => {
      pending.delete(id);
      reject(new DOMException("Request aborted", "AbortError"));
      flush();
    };
    const finish = (reply: Reply) => {
      options.signal?.removeEventListener("abort", abort);
      resolve(reply);
    };
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
