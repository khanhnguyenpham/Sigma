import { type ScenarioEditorState } from "../../hooks/useScenarioEditor";

import { ScenarioItemField } from "./ScenarioItemPicker";

import { PolicyFields } from "./PolicyFields";

export function PolicyOverrideEditor({
  editor,
}: {
  editor: ScenarioEditorState;
}) {
  const { overrides, setOverrides, update, chooseItem, pickedItems } =
    editor;
  return (
    <fieldset>
      <legend>Điều chỉnh riêng mặt hàng</legend>
      <p className="caption">
        Chọn mặt hàng theo nhà mạng. Điều chỉnh chỉ áp dụng trong kịch
        bản này.
        Để trống để kế thừa cấu hình sản phẩm có hiệu lực khi tính kế hoạch. ROP lấy giá trị lớn hơn giữa nhu cầu dự báo 7 ngày cộng SS và ngưỡng nhập tối thiểu.
        Lượng nhập mỗi lần lấy từ cấu hình mặt hàng, không thay đổi tại đây.
      </p>
      {overrides.map((row, index) => (
        <div className="scenario-row" key={index}>
          <label>
            Mặt hàng
            {
              <ScenarioItemField name={`điều chỉnh ${index+1}`} itemId={row.item_id} item={pickedItems[Number(row.item_id)]} onChoose={()=>chooseItem('override',index)} />
            }
          </label>
          <PolicyFields
            policy={row}
            override
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
        onClick={() => chooseItem('override')}
      >
        ＋ Điều chỉnh mặt hàng
      </button>
    </fieldset>
  );
}
