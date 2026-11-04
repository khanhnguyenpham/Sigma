const statuses = {
  internal: {
    active: ["Đang nhập hàng", "positive"],
    scheduled_stop: ["Sắp ngừng nhập", "warning"],
    stopped: ["Đã ngừng nhập", "negative"],
  },
  provider: {
    clear: ["Đang cung cấp", "positive"],
    scheduled_stop: ["Sắp ngừng cung cấp", "warning"],
    stopped: ["Đã ngừng cung cấp", "negative"],
    scheduled_resume: ["Chờ cung cấp lại", "warning"],
  },
};

export function ProductStatus({ value, kind }: { value: unknown; kind: keyof typeof statuses }) {
  const state = (statuses[kind] as Record<string, string[]>)[String(value)];
  return <span className={`product-status ${state?.[1] ?? "neutral"}`}><i aria-hidden="true" />{state?.[0] ?? "Chưa có thông tin"}</span>;
}
