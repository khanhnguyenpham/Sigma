export type FilterField =
  | { key: string; label: string; type: "search"; placeholder: string }
  | { key: string; label: string; type: "select"; options: readonly (readonly [string, string])[]; all?: string }
  | { key: string; label: string; type: "date" };

/** One filter row for list pages: text search, selects and date bounds, with a single reset. */
export function FilterBar({ fields, values, onChange, onReset }: {
  fields: FilterField[]; values: Record<string, string>; onChange: (key: string, value: string) => void; onReset: () => void;
}) {
  const active = fields.some((field) => values[field.key]);
  return <div className="ops-filters" role="search">
    {fields.map((field) => <label key={field.key} className={field.type === "search" ? "filter-search" : undefined}>{field.label}
      {field.type === "select" ? <select value={values[field.key] ?? ""} onChange={(event) => onChange(field.key, event.target.value)}>
        <option value="">{field.all ?? "Tất cả"}</option>
        {field.options.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select> : <input type={field.type === "date" ? "date" : "search"} value={values[field.key] ?? ""} maxLength={120}
        placeholder={field.type === "search" ? field.placeholder : undefined} onChange={(event) => onChange(field.key, event.target.value)} />}
    </label>)}
    {active && <button type="button" className="text-button filter-reset" onClick={onReset}>Xóa bộ lọc</button>}
  </div>;
}

export const PRODUCT_TYPES = [["eSIM", "eSIM"], ["physical_SIM", "SIM vật lý"]] as const;
export const PRODUCT_STATUS = [["active", "Đang hoạt động"], ["inactive", "Ngừng nhập"]] as const;

// The products API keeps its original active/include_inactive flags; map the tri-state status onto them.
export function productStatusParams(status: string) {
  return status === "active" ? { active: "true" } : status === "inactive" ? { active: "false" } : { include_inactive: "true" };
}
