import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { State, Table, useResource } from "../src/components/common";
import { RunDialog } from "../src/components/RunDialog";
import {
  ApiError,
  contextUrl,
  readContext,
  fmt,
  type Context,
  type Run,
} from "../src/api/client";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  history.replaceState(null, "", "/");
});
const response = (body: unknown) =>
  ({ ok: true, json: async () => body }) as Response;
describe("Result integrity in the UI", () => {
  it("keeps zero distinct from missing actual", () => {
    expect(fmt(null)).toBe("—");
    expect(fmt(0)).toBe("0");
    render(
      <Table
        rows={[{ actual: null }, { actual: 0 }]}
        columns={[{ key: "actual", label: "Actual" }]}
      />,
    );
    expect(screen.getByText("—")).toBeVisible();
    expect(screen.getByText("0")).toBeVisible();
  });
  it("has explicit loading, empty and conflict states", () => {
    const { rerender } = render(<State loading />);
    expect(screen.getByRole("status")).toBeVisible();
    rerender(<State empty />);
    expect(screen.getByText(/Không có bản ghi/)).toBeVisible();
    rerender(
      <State
        error={new ApiError("version_conflict", "raw database error", 409)}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Cấu hình đã thay đổi");
    expect(screen.queryByText("raw database error")).toBeNull();
  });
  it("round trips the selected run, cutoff and filters through the URL", () => {
    const ctx: Context = {
      runId: "frozen-run",
      warehouseId: "18",
      itemId: "4",
      productType: "eSIM",
      supplierId: "2",
      origin: "2025-10-31",
    };
    history.replaceState(null, "", "?" + contextUrl(ctx) + "#alerts");
    expect(readContext()).toEqual(ctx);
  });
  it("aborts a superseded request and never overwrites the new run with an old response", async () => {
    let oldResolve: (r: Response) => void = () => {};
    let oldSignal: AbortSignal | undefined;
    vi.spyOn(globalThis, "fetch").mockImplementation((input, options) =>
      String(input).endsWith("/old")
        ? ((oldSignal = options?.signal as AbortSignal),
          new Promise((resolve) => {
            oldResolve = resolve;
          }))
        : Promise.resolve(response({ value: "new-run" })),
    );
    function Probe({ path }: { path: string }) {
      const result = useResource<{ value: string }>(path);
      return <div>{result.data?.value ?? "loading"}</div>;
    }
    const { rerender } = render(<Probe path="/old" />);
    rerender(<Probe path="/new" />);
    await screen.findByText("new-run");
    expect(oldSignal?.aborted).toBe(true);
    await act(async () => oldResolve(response({ value: "old-run" })));
    expect(screen.queryByText("old-run")).toBeNull();
  });
  it("double submit enqueues once and retries an identical body with the same key", async () => {
    const bodies: string[] = [],
      keys: string[] = [];
    let finish: (r: Response) => void = () => {};
    vi.spyOn(globalThis, "fetch").mockImplementation((input, options) => {
      if (options?.method === "POST") {
        bodies.push(String(options.body));
        keys.push(
          (options.headers as Record<string, string>)["Idempotency-Key"],
        );
        return new Promise((resolve) => {
          finish = resolve;
        });
      }
      return Promise.resolve(
        response({ items: [{ id: 1, name: "Base", version: 1 }], total: 1 }),
      );
    });
    const runs = [
      {
        id: "forecast",
        kind: "forecast",
        status: "complete",
        source_import_run_id: "source",
        as_of_date: "2025-12-31",
        result_summary: { routes: 46 },
        observation_end: "2025-12-31",
        forecast_run_id: null,
        scenario_id: null,
        config_version: "fixture",
        assumption_version: "fixture",
        target_version: "fixture",
        error_code: null,
        period_start: null,
        period_end: null,
        created_at: "2026-10-19T00:00:00Z",
      },
    ] satisfies Run[];
    const created = vi.fn();
    render(<RunDialog runs={runs} onClose={() => {}} onCreated={created} />);
    await screen.findByText("Base · v1");
    const form = screen
      .getByRole("button", { name: "Bắt đầu lượt chạy" })
      .closest("form")!;
    fireEvent.submit(form);
    fireEvent.submit(form);
    expect(bodies).toHaveLength(1);
    await act(async () =>
      finish({
        ok: false,
        status: 503,
        json: async () => ({
          error: { code: "database_unavailable", message: "offline" },
        }),
      } as Response),
    );
    await screen.findByRole("alert");
    fireEvent.submit(form);
    expect(keys[1]).toBe(keys[0]);
    expect(bodies[1]).toBe(bodies[0]);
    await act(async () => finish(response({ run_id: "new-run" })));
    await waitFor(() => expect(created).toHaveBeenCalledWith("new-run"));
  });
});
