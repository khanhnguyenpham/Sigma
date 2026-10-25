import { type Row } from "../../types/api";

export function ItemSelect({
  name,
  value,
  onChange,
  itemOptions,
}: {
  name: string;
  value: unknown;
  onChange?: (id: number) => void;
  itemOptions: Row[];
}) {
  return (
    <select
      name={name}
      required
      value={value === undefined ? undefined : String(value)}
      onChange={onChange ? (e) => onChange(Number(e.target.value)) : undefined}
    >
      <option value="">Chọn mặt hàng</option>
      {value && !itemOptions.some((i) => String(i.id) === String(value)) ? (
        <option value={String(value)}>
          Mặt hàng #{String(value)} · đã chọn ở kho khác
        </option>
      ) : null}
      {itemOptions.map((i) => (
        <option key={String(i.id)} value={String(i.id)}>
          {String(i.sku)} · {String(i.product_type)}
        </option>
      ))}
    </select>
  );
}
