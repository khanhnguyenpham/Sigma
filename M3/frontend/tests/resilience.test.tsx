import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { State } from "../src/components/ui/State";
import { useResource } from "../src/hooks/useResource";
import { PageBoundary } from "../src/components/ui/PageBoundary";
import { HelpDialog } from "../src/components/dialogs/HelpDialog";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
it("recovers a failed read on explicit retry without a page reload", async () => {
  const fetcher = vi
    .spyOn(globalThis, "fetch")
    .mockRejectedValueOnce(new Error("Offline"))
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ quantity: 7 }),
    } as Response);
  function Example() {
    const r = useResource<{ quantity: number }>("/inventory");
    return (
      <>
        <State error={r.error} loading={r.loading} />
        {r.data && <p>Stock {r.data.quantity}</p>}
      </>
    );
  }
  render(<Example />);
  fireEvent.click(await screen.findByRole("button", { name: "Thử tải lại" }));
  expect(await screen.findByText("Stock 7")).toBeVisible();
  expect(fetcher).toHaveBeenCalledTimes(2);
});
it("isolates a rendering failure and opens the page again when the issue is cleared", () => {
  vi.spyOn(console, "error").mockImplementation(() => {});
  let fail = true;
  function Broken() {
    if (fail) throw new Error("simulated");
    return <p>Inventory restored</p>;
  }
  render(
    <PageBoundary>
      <Broken />
    </PageBoundary>,
  );
  expect(screen.getByRole("alert")).toBeVisible();
  fail = false;
  fireEvent.click(screen.getByRole("button", { name: "Thử mở lại" }));
  expect(screen.getByText("Inventory restored")).toBeVisible();
});
it("offers operational help and supports Escape without changing a plan", () => {
  const close = vi.fn();
  render(<HelpDialog onClose={close} />);
  expect(screen.getByRole("dialog", { name: "Sử dụng SIGMA" })).toBeVisible();
  expect(screen.getByText("Vị thế tồn (IP)")).toBeVisible();
  fireEvent.keyDown(document, { key: "Escape" });
  expect(close).toHaveBeenCalledTimes(1);
});
