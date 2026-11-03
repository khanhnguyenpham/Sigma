import { afterEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { RunRetry } from "../src/components/dialogs/RunRetry";

afterEach(() => vi.restoreAllMocks());

it("keeps retry identity after a quota error and prevents duplicate submissions", async () => {
  const created = vi.fn();
  let finish: (response: Response) => void = () => {};
  const fetcher = vi.spyOn(globalThis, "fetch").mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  render(<RunRetry id="failed-run" onCreated={created} />);
  const button = screen.getByRole("button", { name: "Thử lại với cấu hình hiện tại" });
  fireEvent.click(button); fireEvent.click(button);
  expect(fetcher).toHaveBeenCalledTimes(1);
  finish({ ok: false, status: 429, json: async () => ({ error: { code: "demo_queue_full", message: "Hàng đợi đang đầy.", details: { retry_after_seconds: 60 } } }) } as Response);
  expect(await screen.findByRole("alert")).toHaveTextContent("Thử lại sau 60 giây");
  fetcher.mockResolvedValueOnce({ ok: true, json: async () => ({ run_id: "new-run" }) } as Response);
  fireEvent.click(button);
  await waitFor(() => expect(created).toHaveBeenCalledWith("new-run"));
  expect(fetcher.mock.calls[0][1]?.headers).toEqual(fetcher.mock.calls[1][1]?.headers);
  expect(fetcher.mock.calls[0][0]).toContain("/runs/failed-run/retry");
});
