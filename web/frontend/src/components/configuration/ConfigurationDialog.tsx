import { errorLabel } from "../../utils/labels";

import { type ConfigurationState } from "../../hooks/useConfiguration";

import { PolicyForm } from "./PolicyForm";

import { ScenarioForm } from "./ScenarioForm";
import { warehouseName } from "../../utils/warehouse";

export function ConfigurationDialog({
  editor,
}: {
  editor: ConfigurationState;
}) {
  const {
    city,
    policy,
    newScenario,
    warehouse,
    setWarehouse,
    warehouses,
    setCity,
    setPolicy,
    setNewScenario,
    save,
    busy,
    error,
  } = editor;
  return (
    <div className="modal-shade">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="config-title"
      >
        <button
          className="close"
          aria-label="Đóng cấu hình"
          onClick={() => {
            setCity(undefined);
            setPolicy(undefined);
            setNewScenario(false);
          }}
        >
          ×
        </button>
        <h2 id="config-title">
          {city
            ? "Thành phố giả định"
            : policy
              ? "Policy phiên bản mới"
              : "Kịch bản mô phỏng"}
        </h2>
        <form
          onSubmit={(e) =>
            save(e, city ? "city" : policy ? "policy" : "scenario")
          }
        >
          {(newScenario || (policy && !policy.item_id)) && (
            <label>
              Kho để chọn mặt hàng
              <select
                value={warehouse}
                onChange={(e) => setWarehouse(e.target.value)}
              >
                <option value="">Chọn kho / tuyến</option>
                {warehouses.data?.items.map((w) => (
                  <option key={String(w.id)} value={String(w.id)}>
                    {warehouseName(w)}
                  </option>
                ))}
              </select>
            </label>
          )}
          {city && (
            <label>
              Thành phố
              <input
                name="city"
                defaultValue={String(city.city)}
                required
                maxLength={100}
              />
            </label>
          )}
          {policy && <PolicyForm editor={editor} policy={policy} />}
          {newScenario && <ScenarioForm editor={editor} />}
          <div className="notice subtle">
            Lưu cấu hình không tự thay kết quả. Chạy một phương án mới để xem
            tác động.
          </div>
          <button className="primary" disabled={busy}>
            {busy ? "Đang lưu…" : "Lưu phiên bản mới"}
          </button>
          {error && (
            <div role="alert" className="notice error">
              {errorLabel(error)}
            </div>
          )}
        </form>
      </section>
    </div>
  );
}
