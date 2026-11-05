import { type ScenarioEditorState } from "../../hooks/useScenarioEditor";

import { PolicyOverrideEditor } from "./PolicyOverrideEditor";

import { ReceiptEditor } from "./ReceiptEditor";
import { ScenarioSupplyEditor } from "./ScenarioSupplyEditor";

export function ScenarioForm({ editor }: { editor: ScenarioEditorState }) {
  const field = (key: string, value: unknown) => editor.setValues((previous) => ({ ...previous, [key]: value }));
  return (
    <>
      <label>
        Tên kịch bản
        <input name="name" required maxLength={120} value={String(editor.values.name)} onChange={(event) => field("name", event.target.value)} />
      </label>
      <label>
        Mã kịch bản
        <input name="code" pattern="[a-z0-9_-]+" required maxLength={64} value={String(editor.values.code)} onChange={(event) => field("code", event.target.value)} />
      </label>
      <label>
        {"Tồn đầu · số ngày phủ"}
        <select name="cover_days" value={String(editor.values.cover_days)} onChange={(event) => field("cover_days", event.target.value)}>
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
          value={String(editor.values.safety_multiplier)}
          onChange={(event) => field("safety_multiplier", event.target.value)}
          required
        />
      </label>
      <label>
        Ghi chú
        <textarea name="description" maxLength={1000} value={String(editor.values.description)} onChange={(event) => field("description", event.target.value)} />
      </label>
      <PolicyOverrideEditor editor={editor} />
      <ReceiptEditor editor={editor} />
      <ScenarioSupplyEditor editor={editor} />
    </>
  );
}
