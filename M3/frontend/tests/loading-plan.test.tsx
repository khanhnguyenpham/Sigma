import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import App from "../src/App";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  history.replaceState(null, "", "/");
});
it("does not present a missing-plan empty state while the selected plan is still loading", async () => {
  history.replaceState(null, "", "/?run_id=pending#inventory");
  vi.spyOn(globalThis, "fetch").mockImplementation((url) => {
    const path = String(url);
    if (path === "/api/v1/runs/pending") return new Promise(() => {});
    const items = path.startsWith("/api/v1/runs?")
      ? [
          {
            id: "old",
            kind: "stock_projection",
            status: "complete",
            as_of_date: "2025-10-31",
            result_summary: {},
          },
        ]
      : [];
    return Promise.resolve({
      ok: true,
      json: async () => ({ items, total: items.length }),
    } as Response);
  });
  render(<App />);
  await vi.waitFor(() =>
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/runs/pending",
      expect.anything(),
    ),
  );
  expect(screen.queryByText("Chưa có kế hoạch")).toBeNull();
  expect(screen.getAllByRole("status").length).toBeGreaterThan(0);
});
