import { useState } from "react";
import { api, type Page, type Row, query, errorLabel } from "../api/client";
import {
  useResource,
  Panel,
  Table,
  State,
  Pager,
  useDialogFocus,
} from "../components/common";
export function Configuration({ onChanged }: { onChanged: () => void }) {
  const [tab, setTab] = useState("warehouses"),
    [page, setPage] = useState(1),
    [version, setVersion] = useState(0),
    [message, setMessage] = useState(""),
    [error, setError] = useState<Error>(),
    [busy, setBusy] = useState(false);
  const [city, setCity] = useState<Row>(),
    [policy, setPolicy] = useState<Row>(),
    [newScenario, setNewScenario] = useState(false),
    [warehouse, setWarehouse] = useState(""),
    [overrides, setOverrides] = useState<Row[]>([]),
    [receipts, setReceipts] = useState<Row[]>([]);
  useDialogFocus(!!city || !!policy || newScenario, () => {
    setCity(undefined);
    setPolicy(undefined);
    setNewScenario(false);
  });
  const data = useResource<Page>(
    `/${tab === "policies" ? "supplier-item-policies" : tab}?${query({ page, page_size: 50, refresh: undefined })}&v=${version}`,
  );
  const supplierData = useResource<Page>("/suppliers?page_size=100");
  const warehouses = useResource<Page>("/warehouses?page_size=100");
  const itemData = useResource<Page>(
    warehouse ? `/items?warehouse_id=${warehouse}&page_size=100` : null,
  );
  const itemOptions = itemData.data?.items ?? [];
  const itemSelect = (
    name: string,
    value: unknown,
    onChange?: (id: number) => void,
  ) => (
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
  const update = (
    _rows: Row[],
    setter: React.Dispatch<React.SetStateAction<Row[]>>,
    index: number,
    key: string,
    value: unknown,
  ) =>
    setter((previous) =>
      previous.map((r, i) => (i === index ? { ...r, [key]: value } : r)),
    );
  function updateReceiptDate(index: number, ordered: string) {
    const date = new Date(ordered + "T00:00:00Z");
    date.setUTCDate(date.getUTCDate() + 7);
    const eta = Number.isNaN(date.valueOf())
      ? ""
      : date.toISOString().slice(0, 10);
    setReceipts((previous) =>
      previous.map((r, i) =>
        i === index ? { ...r, ordered_on: ordered, eta } : r,
      ),
    );
  }
  async function save(event: React.FormEvent<HTMLFormElement>, kind: string) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(undefined);
    setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      let path = "",
        method = "POST",
        body: Row = {};
      if (kind === "city") {
        path = `/warehouses/${city?.id}`;
        method = "PATCH";
        body = {
          city: String(form.get("city")),
          expected_version: city?.version,
        };
      }
      if (kind === "policy") {
        path = "/supplier-item-policies";
        body = {
          item_id: Number(form.get("item_id")),
          supplier_id: Number(form.get("supplier_id")),
          effective_from: String(form.get("effective_from")),
          configured_rop_floor: Number(form.get("configured_rop_floor")),
          moq: Number(form.get("moq")),
          safety_days: Number(form.get("safety_days")),
          expected_version: policy?.version ?? 0,
        };
      }
      if (kind === "scenario") {
        path = "/scenarios";
        body = {
          name: String(form.get("name")),
          code: String(form.get("code")),
          description: String(form.get("description") ?? ""),
          settings: {
            cover_days: Number(form.get("cover_days")),
            safety_multiplier: Number(form.get("safety_multiplier")),
            policy_overrides: overrides,
            receipts_initial: receipts,
            receipts_declared: true,
          },
        };
      }
      await api(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setCity(undefined);
      setPolicy(undefined);
      setNewScenario(false);
      setVersion((v) => v + 1);
      setMessage(
        "Đã lưu phiên bản mới. Phương án đang xem vẫn giữ dữ liệu và cấu hình cũ.",
      );
      onChanged();
    } catch (e) {
      setError(e as Error);
    } finally {
      setBusy(false);
    }
  }
  const columns =
    tab === "warehouses"
      ? [
          { key: "code", label: "Kho" },
          { key: "destination_country", label: "Điểm đến" },
          { key: "carrier", label: "Nhà mạng" },
          { key: "city", label: "Thành phố giả định" },
          { key: "version", label: "Phiên bản" },
        ]
      : tab === "policies"
        ? [
            { key: "item_label", label: "Mặt hàng" },
            { key: "supplier_code", label: "Nhà cung cấp" },
            { key: "version", label: "Phiên bản" },
            { key: "effective_from", label: "Từ ngày" },
            { key: "effective_to", label: "Đến trước ngày" },
            { key: "configured_rop_floor", label: "Ngưỡng nhập tối thiểu" },
            { key: "moq", label: "Lượng tối thiểu (MOQ)" },
            { key: "safety_days", label: "Số ngày tồn an toàn" },
          ]
        : [
            { key: "code", label: "Mã" },
            { key: "name", label: "Tên kịch bản" },
            { key: "version", label: "Phiên bản" },
            { key: "description", label: "Ghi chú" },
          ];
  return (
    <>
      <div className="page-intro">
        <h1>Cấu hình kho & nhập hàng</h1>
        <p>
          Quản lý kho, chính sách nhà cung cấp và kịch bản mô phỏng. Mỗi lần lưu
          tạo phiên bản mới.
        </p>
      </div>
      {message && (
        <div className="notice success" role="status">
          {message}
        </div>
      )}
      {error && (
        <div className="notice error" role="alert">
          {errorLabel(error)}
        </div>
      )}
      <Panel
        title="Danh mục và chính sách hiện tại"
        note="Danh mục hiện tại dùng để thiết lập phương án mới. Kết quả cũ giữ danh mục và cấu hình tại lúc tạo."
        action={
          <div className="segments">
            {[
              ["warehouses", "Kho"],
              ["policies", "Chính sách nhập hàng"],
              ["scenarios", "Kịch bản"],
            ].map(([id, name]) => (
              <button
                key={id}
                className={tab === id ? "active" : ""}
                onClick={() => {
                  setTab(id);
                  setPage(1);
                  setError(undefined);
                }}
              >
                {name}
              </button>
            ))}
          </div>
        }
      >
        <State loading={data.loading} error={data.error} />
        <Table
          rows={data.data?.items ?? []}
          columns={columns}
          onRow={(r) => {
            if (tab === "warehouses") setCity(r);
            if (tab === "policies") setPolicy(r);
          }}
        />
        <Pager page={page} total={data.data?.total ?? 0} onChange={setPage} />
        {tab === "policies" && (
          <button
            className="secondary"
            onClick={() => setPolicy({ version: 0 })}
          >
            ＋ Policy cho mặt hàng chưa cấu hình
          </button>
        )}
        {tab === "scenarios" && (
          <button
            className="secondary"
            onClick={() => {
              setNewScenario(true);
              setOverrides([]);
              setReceipts([]);
            }}
          >
            ＋ Kịch bản mới
          </button>
        )}
      </Panel>
      {(city || policy || newScenario) && (
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
                        {String(w.destination_country)} / {String(w.carrier)}
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
              {policy && (
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
                      itemSelect("item_id", undefined)
                    )}
                  </label>
                  <label>
                    Nhà cung cấp
                    <select
                      name="supplier_id"
                      defaultValue={String(
                        policy.supplier_id ??
                          supplierData.data?.items[0]?.id ??
                          "",
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
                  <div className="form-grid">
                    <label>
                      Ngưỡng nhập tối thiểu (ROP floor)
                      <input
                        name="configured_rop_floor"
                        type="number"
                        min="0"
                        step="1"
                        required
                        defaultValue={Number(policy.configured_rop_floor ?? 0)}
                      />
                    </label>
                    <label>
                      MOQ
                      <input
                        name="moq"
                        type="number"
                        min="1"
                        step="1"
                        required
                        defaultValue={Number(policy.moq ?? 5)}
                      />
                    </label>
                  </div>
                  <label>
                    Số ngày tồn an toàn
                    <input
                      name="safety_days"
                      type="number"
                      min="0"
                      step="0.001"
                      required
                      defaultValue={Number(policy.safety_days ?? 2)}
                    />
                  </label>
                  <p className="caption">
                    Nhập kho7ngày, review1ngày cố định. Ngày hiệu lực ảnh hưởng
                    phương án cũ sẽ bị chặn; dùng điều chỉnh riêng trong kịch
                    bản để thử lại lịch sử.
                  </p>
                </>
              )}
              {newScenario && (
                <>
                  <label>
                    Tên kịch bản
                    <input name="name" required maxLength={120} />
                  </label>
                  <label>
                    Mã kịch bản
                    <input
                      name="code"
                      pattern="[a-z0-9_-]+"
                      required
                      maxLength={64}
                    />
                  </label>
                  <label>
                    Tồn đầu · số ngày phủ
                    <select name="cover_days" defaultValue="7">
                      <option>3</option>
                      <option>7</option>
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
                  <fieldset>
                    <legend>Điều chỉnh riêng mặt hàng</legend>
                    <p className="caption">
                      Đổi kho phía trên để chọn mặt hàng. Điều chỉnh chỉ áp dụng
                      trong kịch bản này.
                    </p>
                    {overrides.map((row, index) => (
                      <div className="scenario-row" key={index}>
                        <label>
                          Mặt hàng
                          {itemSelect(
                            "override_item_" + index,
                            row.item_id,
                            (id) =>
                              update(
                                overrides,
                                setOverrides,
                                index,
                                "item_id",
                                id,
                              ),
                          )}
                        </label>
                        <div className="form-grid">
                          <label>
                            Ngưỡng nhập tối thiểu (ROP floor)
                            <input
                              type="number"
                              min="0"
                              step="1"
                              required
                              value={Number(row.configured_rop_floor)}
                              onChange={(e) =>
                                update(
                                  overrides,
                                  setOverrides,
                                  index,
                                  "configured_rop_floor",
                                  Number(e.target.value),
                                )
                              }
                            />
                          </label>
                          <label>
                            MOQ
                            <input
                              type="number"
                              min="1"
                              step="1"
                              required
                              value={Number(row.moq)}
                              onChange={(e) =>
                                update(
                                  overrides,
                                  setOverrides,
                                  index,
                                  "moq",
                                  Number(e.target.value),
                                )
                              }
                            />
                          </label>
                        </div>
                        <label>
                          Số ngày tồn an toàn
                          <input
                            type="number"
                            min="0"
                            step="0.001"
                            required
                            value={Number(row.safety_days)}
                            onChange={(e) =>
                              update(
                                overrides,
                                setOverrides,
                                index,
                                "safety_days",
                                Number(e.target.value),
                              )
                            }
                          />
                        </label>
                        <button
                          type="button"
                          onClick={() =>
                            setOverrides(
                              overrides.filter((_, i) => i !== index),
                            )
                          }
                        >
                          Xóa điều chỉnh
                        </button>
                      </div>
                    ))}
                    <button
                      type="button"
                      disabled={
                        !warehouse || itemData.loading || !itemOptions.length
                      }
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
                  <fieldset>
                    <legend>Lô đang về đã biết tại origin</legend>
                    {receipts.map((row, index) => (
                      <div className="scenario-row" key={index}>
                        <label>
                          Mặt hàng
                          {itemSelect(
                            "receipt_item_" + index,
                            row.item_id,
                            (id) =>
                              update(
                                receipts,
                                setReceipts,
                                index,
                                "item_id",
                                id,
                              ),
                          )}
                        </label>
                        <label>
                          Ngày đặt
                          <input
                            type="date"
                            required
                            value={String(row.ordered_on)}
                            onInput={(e) =>
                              updateReceiptDate(index, e.currentTarget.value)
                            }
                            onChange={(e) =>
                              updateReceiptDate(index, e.currentTarget.value)
                            }
                          />
                        </label>
                        <label>
                          ETA = ngày đặt +7
                          <input readOnly value={String(row.eta)} />
                        </label>
                        <label>
                          Số lượng
                          <input
                            type="number"
                            required
                            min="1"
                            step="1"
                            value={Number(row.ordered_qty)}
                            onChange={(e) =>
                              update(
                                receipts,
                                setReceipts,
                                index,
                                "ordered_qty",
                                Number(e.target.value),
                              )
                            }
                          />
                        </label>
                        <button
                          type="button"
                          onClick={() =>
                            setReceipts(receipts.filter((_, i) => i !== index))
                          }
                        >
                          Xóa lô
                        </button>
                      </div>
                    ))}
                    <button
                      type="button"
                      disabled={
                        !warehouse || itemData.loading || !itemOptions.length
                      }
                      onClick={() =>
                        setReceipts([
                          ...receipts,
                          {
                            item_id: Number(itemOptions[0]?.id ?? 0),
                            ordered_on: "2025-09-30",
                            eta: "2025-10-07",
                            ordered_qty: 10,
                            lot_key: crypto.randomUUID(),
                          },
                        ])
                      }
                    >
                      ＋ Lô đang về
                    </button>
                    <p className="caption">
                      Danh sách trống nghĩa không có lô đầu kỳ. Lô đặt sau
                      origin hoặc trùng mã sẽ bị từ chối.
                    </p>
                  </fieldset>
                </>
              )}
              <div className="notice subtle">
                Lưu cấu hình không tự thay kết quả. Chạy một phương án mới để
                xem tác động.
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
      )}
    </>
  );
}
