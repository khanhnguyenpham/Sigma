import { beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
const bridge = vi.hoisted(() => ({ prepare: vi.fn() }));
vi.mock("../src/api/cloud", () => ({
  CLOUD: true,
  prepareCloudCsv: bridge.prepare,
}));
import { ExportButton } from "../src/components/common";
beforeEach(() => {
  cleanup();
  bridge.prepare.mockReset();
  URL.revokeObjectURL = vi.fn();
});
it("offers a user-clicked download and discards a prepared file when scope changes", async () => {
  bridge.prepare.mockResolvedValue("blob:scope-a");
  const view = render(<ExportButton url="/a/export" />);
  fireEvent.click(screen.getByRole("button", { name: "Xuất CSV" }));
  const link = await screen.findByRole("link", { name: "Tải CSV" });
  expect(link.getAttribute("href")).toBe("blob:scope-a");
  expect(link.getAttribute("download")).toBe("sigma_export.csv");
  view.rerender(<ExportButton url="/b/export" />);
  await waitFor(() =>
    expect(screen.queryByRole("link", { name: "Tải CSV" })).toBeNull(),
  );
  expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:scope-a");
});
it("does not offer a stale download when an old export resolves after a context change", async () => {
  let resolve!: (value: string) => void;
  bridge.prepare.mockReturnValue(
    new Promise<string>((r) => {
      resolve = r;
    }),
  );
  const view = render(<ExportButton url="/old/export" />);
  fireEvent.click(screen.getByRole("button", { name: "Xuất CSV" }));
  view.rerender(<ExportButton url="/new/export" />);
  resolve("blob:old");
  await waitFor(() =>
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:old"),
  );
  expect(screen.queryByRole("link", { name: "Tải CSV" })).toBeNull();
});
