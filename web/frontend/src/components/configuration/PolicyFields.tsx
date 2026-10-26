import type { Row } from "../../types/api";
export function PolicyFields({
  policy,
  onChange,
  override = false,
}: {
  policy: Row;
  onChange: (key: string, value: number | string | undefined) => void;
  override?: boolean;
}) {
  const number = (key: string, label: string, min: number, step: number | string, max?: number) => (
    <label>
      {label}
      <input name={key} value={policy[key] == null ? "" : Number(policy[key])}
        onChange={(event) => onChange(key, event.target.value === "" ? undefined : Number(event.target.value))}
        type="number" min={min} max={max} step={step} required={!override}
        placeholder={override ? "Kế thừa policy" : undefined} />
    </label>
  );
  const hidden = (key: string) => !override && <input type="hidden" name={key} value={String(policy[key] ?? "")} />;
  return (
    <>
      <div className="form-grid">
        {number("configured_rop_floor", "Ngưỡng nhập tối thiểu (ROP floor)", 0, 1)}
        {number("moq", "MOQ", 1, 1)}
      </div>
      <label>
        Cách tính tồn an toàn (SS)
        <select name="safety_mode" value={String(policy.safety_mode ?? "")}
          onChange={(event) => onChange("safety_mode", event.target.value || undefined)} required={!override}>
          {override && <option value="">Kế thừa policy</option>}
          <option value="days">Theo số ngày bán</option>
          <option value="volatility">Theo biến động số bán</option>
        </select>
      </label>
      {policy.safety_mode === "days"
        ? number("safety_days", "Số ngày tồn an toàn", 0, 0.001)
        : hidden("safety_days")}
      {policy.safety_mode === "volatility" ? <div className="form-grid">
        {number("safety_lookback_days", "Số ngày lịch sử quan sát", 7, 1, 90)}
        {number("safety_factor", "Hệ số biến động", 0, "any")}
      </div> : <>{hidden("safety_lookback_days")}{hidden("safety_factor")}</>}
      <label>
        Cách tính ngưỡng nhập (ROP)
        <select name="rop_mode" value={String(policy.rop_mode ?? "")}
          onChange={(event) => onChange("rop_mode", event.target.value || undefined)} required={!override}>
          {override && <option value="">Kế thừa policy</option>}
          <option value="forecast">Theo dự báo bán và tồn an toàn</option>
          <option value="fixed">Ngưỡng cố định</option>
        </select>
      </label>
      {policy.rop_mode === "fixed" && <p className="caption">ROP bằng ngưỡng nhập tối thiểu đã nhập, không cộng tồn an toàn lần nữa.</p>}
      {number("warning_horizon_days", "Số ngày nhìn trước cảnh báo xuống ROP", 1, 1, 14)}
      <p className="caption">Cảnh báo tìm lần dự kiến xuống ROP trong N ngày. N không phải số ngày báo trước lúc cạn hoặc tỷ lệ báo sớm đạt được.</p>
    </>
  );
}
