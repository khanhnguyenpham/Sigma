import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
const mock = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("../src/api/cloud", () => ({
  CLOUD: true,
  cloudRequest: mock.request,
  prepareCloudCsv: vi.fn(),
}));
import { RunDialog } from "../src/components/RunDialog";
import type { Run } from "../src/api/client";
const forecast = {
  id: "forecast",
  kind: "forecast",
  status: "complete",
  source_import_run_id: "source",
  result_summary: {
    origins: 185,
    stock_projection_origins: ["2025-10-31", "2025-12-31"],
  },
} as unknown as Run;
beforeEach(() => {
  mock.request.mockReset();
});
afterEach(cleanup);
it("only offers origins with both a complete stock seed and forecast and prevents sending while scenarios load", async () => {
  let resolve!: (v: unknown) => void;
  mock.request.mockImplementation((path: string) =>
    path.startsWith("/scenarios")
      ? new Promise((r) => {
          resolve = r;
        })
      : Promise.resolve({ ok: true, status: 200, data: { run_id: "new" } }),
  );
  const done = vi.fn();
  render(<RunDialog runs={[forecast]} onClose={() => {}} onCreated={done} />);
  expect(
    screen.getByRole("button", { name: "Bắt đầu lượt chạy" }),
  ).toBeDisabled();
  await screen.findByRole("option", { name: "2025-12-31" });
  expect(screen.queryByRole("option", { name: "2025-07-01" })).toBeNull();
  resolve({
    ok: true,
    status: 200,
    data: { items: [{ id: 1, name: "Base", version: 1 }] },
  });
  await screen.findByRole("option", { name: "Base · v1" });
  const date = screen.getByLabelText("Mốc chốt UTC");
  fireEvent.change(date, { target: { value: "2025-12-31" } });
  fireEvent.click(screen.getByRole("button", { name: "Bắt đầu lượt chạy" }));
  await vi.waitFor(() => expect(done).toHaveBeenCalledWith("new"));
  const call = mock.request.mock.calls.find((c) => c[0] === "/runs");
  expect(JSON.parse(call![1].body).as_of_date).toBe("2025-12-31");
});
it("prevents creating a plan when a forecast has no supported stock dates", async () => {
  mock.request.mockResolvedValue({
    ok: true,
    status: 200,
    data: { items: [{ id: 1, name: "Base", version: 1 }] },
  });
  render(
    <RunDialog
      runs={[{ ...forecast, result_summary: {} }]}
      onClose={() => {}}
      onCreated={() => {}}
    />,
  );
  await screen.findByRole("option", { name: "Base · v1" });
  expect(
    screen.getByRole("button", { name: "Bắt đầu lượt chạy" }),
  ).toBeDisabled();
  expect(screen.getByText(/Chưa có ngày đồng thời đủ tồn/)).toBeVisible();
});
