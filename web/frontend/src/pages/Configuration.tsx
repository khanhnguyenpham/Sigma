import { errorLabel } from "../utils/labels";
import { Panel } from "../components/ui/Panel";
import { Table } from "../components/ui/Table";
import { State } from "../components/ui/State";
import { Pager } from "../components/ui/Pager";

import { useConfiguration } from "../hooks/useConfiguration";

import { ConfigurationDialog } from "../components/configuration/ConfigurationDialog";

export function Configuration({ onChanged }: { onChanged: () => void }) {
  const editor = useConfiguration(onChanged);
  const {
    tab,
    setTab,
    page,
    setPage,
    message,
    error,
    setError,
    data,
    city,
    setCity,
    policy,
    setPolicy,
    newScenario,
    setNewScenario,
    setOverrides,
    setReceipts,
  } = editor;
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
            { key: "safety_days", label: "Số ngày tồn an toàn", render: (value: unknown, row: Record<string, unknown>) => row.safety_mode === "volatility" ? "—" : String(value ?? "—") },
            { key: "safety_mode", label: "Cách tính SS", render: (value: unknown) => value === "volatility" ? "Biến động số bán" : "Số ngày bán" },
            { key: "safety_lookback_days", label: "Ngày lịch sử", render: (value: unknown, row: Record<string, unknown>) => row.safety_mode === "volatility" ? String(value ?? "—") : "—" },
            { key: "safety_factor", label: "Hệ số biến động", render: (value: unknown, row: Record<string, unknown>) => row.safety_mode === "volatility" ? String(value ?? "—") : "—" },
            { key: "rop_mode", label: "Cách tính ROP", render: (value: unknown) => value === "fixed" ? "Cố định" : "Theo dự báo" },
            { key: "warning_horizon_days", label: "N ngày cảnh báo" },
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
        <ConfigurationDialog editor={editor} />
      )}
    </>
  );
}
