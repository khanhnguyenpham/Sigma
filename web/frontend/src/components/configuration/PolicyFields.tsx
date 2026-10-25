import type { ChangeEvent } from "react";
import type { Row } from "../../types/api";
export function PolicyFields({
  policy,
  onChange,
}: {
  policy: Row;
  onChange?: (key: string, value: number) => void;
}) {
  const bind = (key: string, fallback: number) =>
    onChange
      ? {
          value: Number(policy[key]),
          onChange: (event: ChangeEvent<HTMLInputElement>) =>
            onChange(key, Number(event.target.value)),
        }
      : { name: key, defaultValue: Number(policy[key] ?? fallback) };
  return (
    <>
      <div className="form-grid">
        <label>
          Ngưỡng nhập tối thiểu (ROP floor)
          <input
            {...bind("configured_rop_floor", 0)}
            type="number"
            min="0"
            step="1"
            required
          />
        </label>
        <label>
          MOQ
          <input {...bind("moq", 5)} type="number" min="1" step="1" required />
        </label>
      </div>
      <label>
        Số ngày tồn an toàn
        <input
          {...bind("safety_days", 2)}
          type="number"
          min="0"
          step="0.001"
          required
        />
      </label>
    </>
  );
}
