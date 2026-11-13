import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { C00Evaluation } from "../src/components/alerts/C00Evaluation";
import report from "../src/data/c00-forecast-floor-evaluation.json";

afterEach(cleanup);

it("shows the verified full-period C00 evaluation with its distinct protocol and provenance", () => {
  render(<C00Evaluation />);
  expect(screen.getByRole("heading", { name: "Đánh giá C00 — hồi cứu toàn kỳ" })).toBeVisible();
  expect(screen.getByText("46,93%")).toBeVisible();
  expect(screen.getByText("107/228 đợt cạn có đủ thời gian báo sớm")).toBeVisible();
  expect(screen.getByText(/1 đợt thiếu cơ hội báo sớm.*107\/229 \(46,72%\)/)).toBeInTheDocument();
  expect(screen.getByText("76,42%")).toBeVisible();
  expect(screen.getByText("93,45%")).toBeVisible();
  expect(screen.getByText("4,71 ngày")).toBeVisible();
  expect(screen.getByText("29/10/2025 – 31/12/2025")).toBeVisible();
  expect(screen.getByText(/không thay theo kịch bản hoặc bộ lọc/)).toBeVisible();
  expect(screen.getByText(/tự bổ sung hàng và 28 ngày khởi tạo/)).toBeVisible();
  expect(screen.getByText(/ROP = max/)).toBeVisible();
  expect(screen.getByText(/nhập cố định 15 đơn vị mỗi lần/)).toBeInTheDocument();
  expect(screen.getByText(/Bản ROP cố định trước đây đạt 54,02% \(450\/833\)/)).toBeInTheDocument();
  const link = screen.getByRole("link", { name: "Tải kết quả C00" });
  expect(link.getAttribute("href")).toMatch(/c00-forecast-floor-evaluation.*\.json/);
  expect(link.getAttribute("href")).not.toMatch(/^data:|^blob:/);
  const exported = report;
  expect(exported.early_rate).toBe(exported.early_numerator / exported.event_denominator);
  expect(exported.eligible_early_rate).toBe(exported.early_numerator / exported.eligible_event_count);
  expect(Object.values(exported.eligibility_reasons).reduce((sum, count) => sum + count, 0)).toBe(exported.event_denominator);
  expect(exported.precision).toBeCloseTo(exported.alarm_tp / (exported.alarm_tp + exported.alarm_fp), 12);
  expect(exported.recall).toBe(exported.matched_events / exported.event_denominator);
  expect(exported.reproduction_sha256).toMatch(/^[a-f0-9]{64}$/);
  expect(exported.policy_snapshot_sha256).toMatch(/^[a-f0-9]{64}$/);
  expect(exported.parent_policy_snapshot_sha256).toMatch(/^[a-f0-9]{64}$/);
  expect(JSON.stringify(exported)).not.toMatch(/C:\\\\|postgresql|password|customer_id|activation/);
});
