import { type Row } from "../../types/api";

import { type ConfigurationState } from "../../hooks/useConfiguration";

import { ItemSelect } from "./ItemSelect";

import { PolicyFields } from "./PolicyFields";
import { useState } from "react";
import { POLICY_DEFAULTS } from "../../config/policy";

export function PolicyForm({
  editor,
  policy,
}: {
  editor: ConfigurationState;
  policy: Row;
}) {
  const { supplierData, itemOptions } = editor;
  const [values, setValues] = useState<Row>({
    configured_rop_floor: 0, safety_days: 2,
    ...POLICY_DEFAULTS, ...policy,
  });
  return (
    <>
      <label>
        Mặt hàng
        {policy.item_id ? (
          <>
            <input
              name="item_id"
              type="hidden"
              value={Number(policy.item_id)}
            />
            <input
              readOnly
              value={String(policy.item_label ?? policy.item_id)}
            />
          </>
        ) : (
          <ItemSelect
            name={"item_id"}
            value={undefined}
            itemOptions={itemOptions}
          />
        )}
      </label>
      <label>
        Nhà cung cấp
        <select
          name="supplier_id"
          defaultValue={String(
            policy.supplier_id ?? supplierData.data?.items[0]?.id ?? "",
          )}
          required
        >
          {supplierData.data?.items.map((s) => (
            <option key={String(s.id)} value={String(s.id)}>
              {String(s.code)} · {String(s.display_name)}
            </option>
          ))}
        </select>
      </label>
      <label>
        Hiệu lực từ
        <input
          name="effective_from"
          type="date"
          required
          defaultValue="2026-01-01"
        />
      </label>
      {policy.moq != null && policy.fixed_order_qty == null && <p className="caption">Cấu hình cũ chỉ có lượng tối thiểu. Hãy nhập lượng cố định mỗi lần; hệ thống không lấy MOQ cũ làm giá trị này.</p>}
      <PolicyFields policy={values} onChange={(key, value) =>
        setValues((previous) => ({ ...previous, [key]: value }))} />

      <p className="caption">
        Nhập kho7ngày, review1ngày cố định. Ngày hiệu lực ảnh hưởng phương án cũ
        sẽ bị chặn; dùng điều chỉnh riêng trong kịch bản để thử lại lịch sử.
      </p>
    </>
  );
}
