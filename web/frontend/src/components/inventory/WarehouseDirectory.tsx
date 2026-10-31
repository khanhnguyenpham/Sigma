import { useState } from "react";
import type { Row } from "../../types/api";
import { fmt } from "../../utils/format";
import { warehouseName } from "../../utils/warehouse";
import { Icon } from "../ui/Icon";
import { Panel } from "../ui/Panel";
import { State } from "../ui/State";

export function WarehouseDirectory({ warehouses, stock, loading, error, onChoose }: {
  warehouses: Row[];
  stock?: Row[];
  loading?: boolean;
  error?: Error;
  onChoose?: (id: string) => void;
}) {
  const [search, setSearch] = useState("");
  const [country, setCountry] = useState("");
  const [carrier, setCarrier] = useState("");
  const normalize = (value: unknown) => String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase();
  const rows = warehouses.filter((w) =>
    (!country || w.destination_country === country) && (!carrier || w.carrier === carrier) &&
    normalize(`${warehouseName(w)} ${w.destination_country}`).includes(normalize(search.trim())),
  );
  const totals = new Map(stock?.map((row) => [String(row.warehouse_id), row]));
  return (
    <Panel title="Danh sách kho" note="Chọn một kho để xem sản phẩm, tình trạng tồn và kế hoạch bổ sung.">
      <div className="warehouse-toolbar">
        <label className="list-search">
          <Icon name="search" size={18} />
          <input type="search" aria-label="Tìm kho" placeholder="Tìm thành phố hoặc quốc gia…"
            value={search} onChange={(e) => setSearch(e.target.value)} />
        </label>
        <label>Quốc gia
          <select aria-label="Quốc gia của kho" value={country} onChange={(e) => setCountry(e.target.value)}>
            <option value="">Tất cả quốc gia</option>
            {[...new Set(warehouses.map((w) => String(w.destination_country)))].sort().map((c) => <option key={c}>{c}</option>)}
          </select>
        </label>
        <label>Nhà mạng
          <select aria-label="Nhà mạng của kho" value={carrier} onChange={(e) => setCarrier(e.target.value)}>
            <option value="">Tất cả nhà mạng</option>
            {[...new Set(warehouses.map((w) => String(w.carrier)))].sort().map((c) => <option key={c}>{c}</option>)}
          </select>
        </label>
        {(search || country || carrier) && <button className="text-button" onClick={() => { setSearch(""); setCountry(""); setCarrier(""); }}>Xóa bộ lọc kho</button>}
      </div>
      <div className="warehouse-list-meta"><span>{rows.length} / {warehouses.length} kho</span><span>Mỗi kho hiện quản lý sản phẩm của một nhà mạng.</span></div>
      <State loading={loading} error={error} empty={!loading && !error && !rows.length} />
      {!loading && !error && <div className="warehouse-grid">
        {rows.map((w) => {
          const s = totals.get(String(w.id));
          return <button className="warehouse-card" key={String(w.id)}
            aria-label={`Mở kho ${warehouseName(w)} tại ${w.destination_country}, nhà mạng ${w.carrier}`}
            onClick={() => onChoose?.(String(w.id))}>
            <div className="warehouse-card-heading">
              <span className="warehouse-icon"><Icon name="warehouse" size={25} /></span>
              <span className="warehouse-location"><h3>{warehouseName(w)}</h3><span>{String(w.destination_country)}</span></span>
              <Icon name="chevron" size={17} />
            </div>
            <span className="carrier-chip">Nhà mạng <strong>{String(w.carrier)}</strong></span>
            <dl className="warehouse-card-metrics">
              <div><dt>Mặt hàng</dt><dd>{fmt(s?.item_count)}</dd></div>
              <div><dt>Tồn hiện có</dt><dd>{fmt(s?.on_hand_units)}</dd></div>
              <div><dt>Cần đặt thêm</dt><dd className={Number(s?.replenish_items) > 0 ? "stock-warning" : ""}>{fmt(s?.replenish_items)}</dd></div>
            </dl>
            <span className="warehouse-card-footer">
              <span>{!s ? "Chưa có số tồn cho ngày đang chọn" : Number(s.replenish_items) > 0 ? `${fmt(s.recommended_units)} đơn vị cần bổ sung` : Number(s.low_stock_items) > 0 ? "Đã có kế hoạch bổ sung" : "Trong ngưỡng tồn"}</span>
              <strong>Xem sản phẩm <Icon name="arrow" size={14} /></strong>
            </span>
          </button>;
        })}
      </div>}
    </Panel>
  );
}
