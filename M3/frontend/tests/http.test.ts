import { afterEach, expect, it, vi } from "vitest";
import { api } from "../src/services/http";

afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

it("times out a read, aborts transport and ignores a late response", async () => {
  vi.useFakeTimers();
  let finish: (value: Response) => void = () => {};
  let signal: AbortSignal | undefined;
  vi.spyOn(globalThis, "fetch").mockImplementation((_, options) => {
    signal = options?.signal as AbortSignal;
    return new Promise(resolve => { finish = resolve; });
  });
  const reply = api("/runs").catch(error => error);
  await vi.advanceTimersByTimeAsync(30_000);
  expect(await reply).toMatchObject({ code: "request_timeout" });
  expect(signal?.aborted).toBe(true);
  finish({ ok: true, json: async () => ({ stale: true }) } as Response);
  expect(await reply).toMatchObject({ code: "request_timeout" });
});

it("never automatically retries a write after its longer deadline", async () => {
  vi.useFakeTimers();
  const fetcher = vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => {}));
  const reply = api("/scenarios", { method: "POST", body: "{}" }).catch(error => error);
  await vi.advanceTimersByTimeAsync(89_999);
  expect(fetcher).toHaveBeenCalledTimes(1);
  await vi.advanceTimersByTimeAsync(1);
  expect(await reply).toMatchObject({ code: "request_timeout" });
  expect(fetcher).toHaveBeenCalledTimes(1);
});

it("cancels a superseded request and releases timeout resources", async () => {
  vi.useFakeTimers();
  vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => {}));
  const controller = new AbortController();
  const reply = api("/old", { signal: controller.signal }).catch(error => error);
  controller.abort();
  expect(await reply).toMatchObject({ name: "AbortError" });
  expect(vi.getTimerCount()).toBe(0);
});
