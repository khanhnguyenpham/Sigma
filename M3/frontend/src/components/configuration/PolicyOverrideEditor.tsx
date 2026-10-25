import { type ConfigurationState } from "../../hooks/useConfiguration";

import { ItemSelect } from "./ItemSelect";

import { PolicyFields } from "./PolicyFields";

export function PolicyOverrideEditor({
  editor,
}: {
  editor: ConfigurationState;
}) {
  const { overrides, setOverrides, update, warehouse, itemData, itemOptions } =
    editor;
  return (
    <fieldset>
      <legend>Điều chỉnh riêng mặt hàng</legend>
      <p className="caption">
        Đổi kho phía trên để chọn mặt hàng. Điều chỉnh chỉ áp dụng trong kịch
        bản này.
      </p>
      {overrides.map((row, index) => (
        <div className="scenario-row" key={index}>
          <label>
            Mặt hàng
            {
              <ItemSelect
                name={"override_item_" + index}
                value={row.item_id}
                onChange={(id) =>
                  update(overrides, setOverrides, index, "item_id", id)
                }
                itemOptions={itemOptions}
              />
            }
          </label>
          <PolicyFields
            policy={row}
            onChange={(key, value) =>
              update(overrides, setOverrides, index, key, value)
            }
          />

          <button
            type="button"
            onClick={() =>
              setOverrides(overrides.filter((_, i) => i !== index))
            }
          >
            Xóa điều chỉnh
          </button>
        </div>
      ))}
      <button
        type="button"
        disabled={!warehouse || itemData.loading || !itemOptions.length}
        onClick={() =>
          setOverrides([
            ...overrides,
            {
              item_id: Number(itemOptions[0]?.id ?? 0),
              configured_rop_floor: 0,
              moq: 5,
              safety_days: 2,
            },
          ])
        }
      >
        ＋ Điều chỉnh mặt hàng
      </button>
    </fieldset>
  );
}
