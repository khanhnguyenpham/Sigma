import type { Row } from "../../types/api";

export function PolicyFields({ policy, onChange, override = false }: {
  policy: Row; onChange: (key: string, value: number | string | undefined) => void; override?: boolean;
}) {
  const number = (key: string, label: string, min: number, step: number | string, max?: number) => <label>{label}
    <input name={key} value={policy[key] == null ? "" : Number(policy[key])}
      onChange={(event) => onChange(key, event.target.value === "" ? undefined : Number(event.target.value))}
      type="number" min={min} max={max} step={step} required={!override}
      placeholder={override ? "Kế thừa cấu hình sản phẩm" : undefined} />
  </label>;
  return <>
    <div className="form-grid">
      {number("configured_rop_floor", "Ngưỡng nhập tối thiểu (ROP)", 0, 1)}
      {!override && number("fixed_order_qty", "Lượng nhập mỗi lần", 1, 1)}
    </div>
    {!override && <p className="caption">Mỗi lần bổ sung dùng đúng lượng đã khai báo khi tồn thấp hơn ROP và hàng đang về chưa đủ mức mục tiêu.</p>}
    {number("safety_days", "Số ngày tồn an toàn", 0, 0.001)}
    <p className="caption">ROP = max(nhu cầu dự báo 7 ngày + SS, ngưỡng nhập tối thiểu). SS tính theo số ngày tồn an toàn × dự báo bình quân ngày × hệ số safety, làm tròn lên.</p>
    {number("warning_horizon_days", "Số ngày nhìn trước cảnh báo xuống ROP", 1, 1, 14)}
    <p className="caption">Cảnh báo khi dự kiến tồn xuống dưới ROP trong số ngày này.</p>
  </>;
}
