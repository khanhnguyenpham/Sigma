import { useState } from "react";
import { Icon } from "../components/ui/Icon";
import { State } from "../components/ui/State";
import { qty, type Warehouse } from "./types";

const normalize = (value: unknown) => String(value ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLocaleLowerCase();

/** Ledger warehouses as cards, same look as the simulation warehouse list; a card opens that warehouse's stock. */
export function WarehouseCards({ warehouses, loading, error, onChoose, onAdd }: {
  warehouses: Warehouse[]; loading: boolean; error?: Error; onChoose: (id: string) => void; onAdd: () => void;
}) {
  const [search, setSearch] = useState(""), [country, setCountry] = useState("");
  const rows = warehouses.filter((w) => (!country || w.country === country) && normalize(`${w.name} ${w.code} ${w.country}`).includes(normalize(search.trim())));
  return <section className="panel ops-list-panel">
    <div className="panel-title"><div><h2>Danh sách kho</h2><p>Chọn một kho để xem sản phẩm, số dư và thao tác xuất kho, kiểm kê.</p></div>
      <button className="primary" disabled={!warehouses.length} onClick={onAdd}>Kiểm kê / tồn đầu</button></div>
    <div className="warehouse-toolbar">
      <label className="list-search"><Icon name="search" size={18} />
        <input type="search" aria-label="Tìm kho" placeholder="Tìm tên, mã kho hoặc quốc gia…" value={search} maxLength={120} onChange={(event) => setSearch(event.target.value)} /></label>
      <label>Quốc gia<select aria-label="Quốc gia của kho" value={country} onChange={(event) => setCountry(event.target.value)}>
        <option value="">Tất cả quốc gia</option>{[...new Set(warehouses.map((w) => w.country))].sort().map((name) => <option key={name}>{name}</option>)}</select></label>
      {(search || country) && <button className="text-button" onClick={() => { setSearch(""); setCountry(""); }}>Xóa bộ lọc kho</button>}
    </div>
    <div className="warehouse-list-meta"><span>{rows.length} / {warehouses.length} kho đang hoạt động</span><span>Số dư theo chứng từ đã ghi sổ.</span></div>
    <State loading={loading} error={error} />
    {!loading && !error && !warehouses.length && <p className="notice">Chưa có kho đang hoạt động, nên chưa có số dư. Thêm kho tại Kho › Kho hàng, rồi nhận hàng hoặc kiểm kê để bắt đầu theo dõi tồn.</p>}
    {!loading && !error && !!warehouses.length && !rows.length && <p className="notice">Không có kho phù hợp với bộ lọc.</p>}
    {!loading && !error && <div className="warehouse-grid">{rows.map((w) => {
      const empty = Number(w.empty_items ?? 0);
      return <button className="warehouse-card" key={w.id} aria-label={`Mở kho ${w.name} tại ${w.country}`} onClick={() => onChoose(String(w.id))}>
        <div className="warehouse-card-heading">
          <span className="warehouse-icon"><Icon name="warehouse" size={25} /></span>
          <span className="warehouse-location"><h3>{w.name}</h3><span>{w.country}</span></span>
          <Icon name="chevron" size={17} />
        </div>
        <span className="carrier-chip">Mã kho <strong>{w.code}</strong></span>
        <dl className="warehouse-card-metrics">
          <div><dt>Mặt hàng còn tồn</dt><dd>{qty(w.stocked_items ?? 0)}</dd></div>
          <div><dt>Tồn hiện có</dt><dd>{qty(w.on_hand_qty ?? 0)}</dd></div>
          <div><dt>Đang về</dt><dd className={Number(w.incoming_qty) > 0 ? "stock-incoming" : ""}>{qty(w.incoming_qty ?? 0)}</dd></div>
        </dl>
        <span className="warehouse-card-footer">
          <span className={empty > 0 ? "stock-warning" : undefined}>{empty > 0 ? `${qty(empty)} mặt hàng đã hết` : w.last_movement_on ? `Biến động gần nhất ${w.last_movement_on}` : "Chưa có chứng từ"}</span>
          <strong>Xem sản phẩm <Icon name="arrow" size={14} /></strong>
        </span>
      </button>;
    })}</div>}
  </section>;
}
