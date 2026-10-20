import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { waitFor } from "@testing-library/react";
const bridge = vi.hoisted(() => ({
  listener: undefined as undefined | ((event: Event) => void),
  send: vi.fn(),
  height: vi.fn(),
  ready: vi.fn(),
}));
vi.mock("streamlit-component-lib", () => ({
  Streamlit: {
    RENDER_EVENT: "render",
    events: {
      addEventListener: (_name: string, listener: (event: Event) => void) => {
        bridge.listener = listener;
      },
    },
    setComponentValue: bridge.send,
    setFrameHeight: bridge.height,
    setComponentReady: bridge.ready,
  },
}));
beforeEach(() => {
  vi.resetModules();
  bridge.listener = undefined;
  bridge.send.mockClear();
  bridge.height.mockClear();
  bridge.ready.mockClear();
});
function render(responses: Record<string, unknown> = {}) {
  const event = new CustomEvent("render", {
    detail: { args: { frame_height: 900, responses } },
  });
  bridge.listener!(event);
}
async function boot() {
  const cloud = await import("../src/api/cloud");
  const start = cloud.initCloud();
  await waitFor(() => expect(bridge.listener).toBeDefined());
  render();
  await start;
  return cloud;
}
it("batches concurrent requests and resolves replies by their own request ids", async () => {
  const cloud = await boot();
  const first = cloud.cloudRequest("/runs"),
    second = cloud.cloudRequest("/scenarios", {
      method: "POST",
      headers: { "Idempotency-Key": "test-idempotency" },
      body: JSON.stringify({ name: "Test" }),
    });
  await waitFor(() => expect(bridge.send).toHaveBeenCalledTimes(1));
  const requests = bridge.send.mock.calls[0][0].requests;
  expect(requests).toHaveLength(2);
  expect(requests[1].body).toEqual({ name: "Test" });
  expect(requests[1].idempotency).toBe("test-idempotency");
  render({
    [requests[1].id]: { ok: true, status: 200, data: { id: 2 } },
    [requests[0].id]: { ok: true, status: 200, data: { total: 5 } },
  });
  expect((await first).data).toEqual({ total: 5 });
  expect((await second).data).toEqual({ id: 2 });
  expect(bridge.ready).toHaveBeenCalledTimes(1);
  expect(bridge.height).toHaveBeenCalledWith(900);
});
it("aborts requests without accepting later stale replies", async () => {
  const cloud = await boot(),
    controller = new AbortController();
  const pending = cloud.cloudRequest("/runs/old", {
    signal: controller.signal,
  });
  const rejected = expect(pending).rejects.toMatchObject({
    name: "AbortError",
  });
  await waitFor(() => expect(bridge.send).toHaveBeenCalledTimes(1));
  const id = bridge.send.mock.calls[0][0].requests[0].id;
  controller.abort();
  await rejected;
  render({ [id]: { ok: true, status: 200, data: { stale: true } } });
  const next = cloud.cloudRequest("/runs/new");
  await waitFor(() => expect(bridge.send).toHaveBeenCalledTimes(2));
  const requests = bridge.send.mock.calls[1][0].requests;
  expect(requests).toHaveLength(1);
  expect(requests[0].path).toBe("/runs/new");
  render({ [requests[0].id]: { ok: true, status: 200, data: { id: "new" } } });
  expect((await next).data).toEqual({ id: "new" });
});

afterEach(() => vi.useRealTimers());
it("times out a disconnected read without accepting a late response or blocking the next request", async () => {
  const cloud = await boot();
  vi.useFakeTimers();
  const task = cloud.cloudRequest("/slow");
  const rejected = expect(task).rejects.toThrow(/Kết nối quá thời gian/);
  await vi.advanceTimersByTimeAsync(30000);
  await rejected;
  const old = bridge.send.mock.calls[0][0].requests[0].id;
  render({ [old]: { ok: true, status: 200, data: { stale: true } } });
  const next = cloud.cloudRequest("/fresh");
  await vi.advanceTimersByTimeAsync(0);
  const requests = bridge.send.mock.calls.at(-1)![0].requests;
  expect(requests).toHaveLength(1);
  render({
    [requests[0].id]: { ok: true, status: 200, data: { fresh: true } },
  });
  expect((await next).data).toEqual({ fresh: true });
});
it("does not retry a timed-out mutation automatically and retains its idempotency key", async () => {
  const cloud = await boot();
  vi.useFakeTimers();
  const task = cloud.cloudRequest("/runs", {
    method: "POST",
    headers: { "Idempotency-Key": "same-write" },
    body: "{}",
  });
  const rejected = expect(task).rejects.toThrow(/có thể đã được xử lý/);
  await vi.advanceTimersByTimeAsync(89999);
  expect(bridge.send).toHaveBeenCalledTimes(1);
  await vi.advanceTimersByTimeAsync(1);
  await rejected;
  expect(bridge.send).toHaveBeenCalledTimes(1);
  expect(bridge.send.mock.calls[0][0].requests[0].idempotency).toBe(
    "same-write",
  );
});
