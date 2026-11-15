import { useEffect, useRef } from "react";
import { useMediaQuery } from "../../hooks/useMediaQuery";
import { ExportButton } from "../ui/ExportButton";
import { Icon } from "../ui/Icon";

export function InventoryActions({ onEdit, onForecast, onReplenishment, exportUrl }: {
  onEdit: () => void; onForecast?: () => void; onReplenishment?: () => void; exportUrl?: string;
}) {
  const compact = useMediaQuery("(max-width: 760px)");
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const outside = (event: PointerEvent) => { if (ref.current && !ref.current.contains(event.target as Node)) ref.current.open = false; };
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, []);
  const edit = <button onClick={onEdit}><Icon name="settings" size={16} /> Chỉnh sửa kho</button>;
  const forecast = onForecast && <button onClick={onForecast}><Icon name="chart" size={16} /> Dự báo nhu cầu</button>;
  const incoming = onReplenishment && <button onClick={onReplenishment}><Icon name="truck" size={16} /> Nhập hàng</button>;
  const csv = exportUrl && <ExportButton url={exportUrl} />;
  if (!compact) return <div className="warehouse-actions">{edit}{forecast}{incoming}{csv}</div>;
  return <div className="warehouse-actions">{incoming}<details ref={ref} className="warehouse-more" onKeyDown={(event) => {
    if (event.key === "Escape") { event.preventDefault(); event.currentTarget.open = false; event.currentTarget.querySelector("summary")?.focus(); }
  }} onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) event.currentTarget.open = false; }}>
    <summary><Icon name="settings" size={16} /> Thao tác kho</summary>
    <div className="warehouse-more-options" onClick={() => { if (ref.current) ref.current.open = false; }}>{edit}{forecast}{csv}</div>
  </details></div>;
}
