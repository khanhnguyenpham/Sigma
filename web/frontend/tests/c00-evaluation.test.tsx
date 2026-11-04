import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { C00Evaluation } from "../src/components/alerts/C00Evaluation";
import report from "../src/data/c00-forecast-floor-evaluation.json";

afterEach(cleanup);

it("shows the verified full-period C00 evaluation with its distinct protocol and provenance", () => {
  render(<C00Evaluation />);
  expect(screen.getByRole("heading", { name: "Đánh giá C00 — hồi cứu toàn kỳ" })).toBeVisible();
  expect(screen.getByText("32,25%")).toBeVisible();
  expect(screen.getByText("129/400 đợt cạn được báo sớm")).toBeVisible();
  expect(screen.getByText("74,06%")).toBeVisible();
  expect(screen.getByText("81,75%")).toBeVisible();
  expect(screen.getByText("5,09 ngày")).toBeVisible();
  expect(screen.getByText("29/10/2025 – 31/12/2025")).toBeVisible();
  expect(screen.getByText(/không thay theo kịch bản hoặc bộ lọc/)).toBeVisible();
  expect(screen.getByText(/tự bổ sung hàng và 28 ngày khởi tạo/)).toBeVisible();
  expect(screen.getByText(/ROP = max/)).toBeVisible();
  expect(screen.getByText(/Bản ROP cố định trước đây: 54,02% = 450\/833/)).toBeInTheDocument();
  const link = screen.getByRole("link", { name: "Tải kết quả C00" });
  expect(link.getAttribute("href")).toMatch(/c00-forecast-floor-evaluation.*\.json/);
  expect(link.getAttribute("href")).not.toMatch(/^data:|^blob:/);
  const exported = report;
  expect(exported.early_rate).toBe(exported.early_numerator / exported.event_denominator);
  expect(exported.precision).toBeCloseTo(exported.alarm_tp / (exported.alarm_tp + exported.alarm_fp), 12);
  expect(exported.recall).toBe(exported.matched_events / exported.event_denominator);
  expect(exported.reproduction_sha256).toMatch(/^[a-f0-9]{64}$/);
  expect(exported.policy_snapshot_sha256).toMatch(/^[a-f0-9]{64}$/);
  expect(JSON.stringify(exported)).not.toMatch(/C:\\\\|postgresql|password|customer_id|activation/);
});
