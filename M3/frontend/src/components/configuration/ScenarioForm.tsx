import { type ConfigurationState } from "../../hooks/useConfiguration";

import { PolicyOverrideEditor } from "./PolicyOverrideEditor";

import { ReceiptEditor } from "./ReceiptEditor";

export function ScenarioForm({ editor }: { editor: ConfigurationState }) {
  return (
    <>
      <label>
        Tên kịch bản
        <input name="name" required maxLength={120} />
      </label>
      <label>
        Mã kịch bản
        <input name="code" pattern="[a-z0-9_-]+" required maxLength={64} />
      </label>
      <label>
        {"Tồn đầu · số ngày phủ"}
        <select name="cover_days" defaultValue="7">
          <option>3</option>
          <option value="7">{"7"}</option>
          <option>14</option>
        </select>
      </label>

      <label>
        Hệ số safety
        <input
          name="safety_multiplier"
          type="number"
          min="0"
          max="10"
          step="0.1"
          defaultValue="1"
          required
        />
      </label>
      <label>
        Ghi chú
        <textarea name="description" maxLength={1000} />
      </label>
      <PolicyOverrideEditor editor={editor} />
      <ReceiptEditor editor={editor} />
    </>
  );
}
