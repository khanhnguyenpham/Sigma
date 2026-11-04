import { useState } from "react";
import type { Row, Run } from "../types/api";
import type { Context } from "../types/context";
import { useResource } from "../hooks/useResource";
import { query } from "../utils/url";
import { warehouseName } from "../utils/warehouse";
import { Panel } from "../components/ui/Panel";
import { State } from "../components/ui/State";
import { ProductStatus } from "../components/products/ProductStatus";
import { ProductSupplyForm } from "../components/products/ProductSupplyForm";
import { ProviderNotices } from "./ProviderNotices";

export function ProductSupply({ ctx, page, run, runs, navigate, onDate, onItem }: {
  ctx: Context; page: string; run?: Run; runs: Run[]; navigate: (page: string) => void;
  onDate: (day: string) => void; onItem: (row: Row) => void;
}) {
  const day = ctx.origin;
  const [revision,setRevision] = useState(0);
  const [action,setAction] = useState<"stop"|"cancel_stop"|"resume">();
  const [message,setMessage] = useState("");
  const product = useResource<Row>(ctx.itemId ? `/products/${ctx.itemId}?${query({as_of_date:day})}` : null,true,revision);
  const row = String(product.data?.id)===ctx.itemId ? product.data : undefined;
  const list = page === "product-supply";
  return <>
    <nav className="warehouse-breadcrumb" aria-label="Đường dẫn lịch cung cấp"><button className="text-button" onClick={()=>navigate("products")}>← Sản phẩm</button>{row&&<><span>/</span><span>{String(row.sku)}</span><span>/</span><span aria-current="page">Lịch cung cấp</span></>}</nav>
    <State loading={product.loading} error={product.error}/>
    {!ctx.itemId&&<p className="notice">Chọn Lịch cung cấp bên cạnh một sản phẩm để tiếp tục.</p>}
    {row&&<>
      <div className="page-heading product-page-heading"><div><h1>Lịch cung cấp</h1><p><strong>{String(row.sku)}</strong> · {row.product_type==="physical_SIM"?"SIM vật lý":"eSIM"} · {warehouseName(row)} · {String(row.carrier)}</p></div><button className="secondary" onClick={()=>navigate("product")}>Cấu hình sản phẩm</button></div>
      {message&&<p role="status" className="notice success">{message}</p>}
      {list&&<>
        <div className="supply-page-context"><label>Ngày thao tác (UTC)<input type="date" value={day} onChange={e=>onDate(e.target.value)}/></label><p>Lịch thay đổi chỉ áp dụng khi tạo kế hoạch mới. Kết quả đã chốt được giữ nguyên.</p></div>
        <Panel title="Nhập hàng tại kho" note="Quản lý việc nhập thêm sản phẩm vào kho này. Ngừng nhập vẫn cho phép bán lượng hàng còn tồn." action={<ProductStatus kind="internal" value={row.internal_status??row.supply_status}/> }>
          <div className="supply-internal-action"><p>{row.internal_status==="stopped"?"Kho đã ngừng nhận đơn nhập mới cho sản phẩm này.":row.internal_status==="scheduled_stop"?"Sản phẩm đã có lịch ngừng nhập tại kho.":"Kho đang được phép đặt thêm sản phẩm này."}</p><button className="secondary" disabled={!day||row.trade_schema_ready!==true} onClick={()=>setAction(row.internal_status==="stopped"?"resume":row.internal_status==="scheduled_stop"?"cancel_stop":"stop")}>{row.internal_status==="stopped"?"Mở nhập lại":row.internal_status==="scheduled_stop"?"Hủy lịch ngừng nhập":"Đặt lịch ngừng nhập"}</button></div>
        </Panel>
      </>}
      <ProviderNotices page={list?"provider-notices":page} day={day} product={row} runs={runs} run={run} navigate={navigate} onItem={onItem} onBack={()=>navigate("product-supply")}/>
      {action&&<ProductSupplyForm product={row} day={day} run={run} action={action} onDate={onDate} onClose={()=>setAction(undefined)} onSaved={()=>{setAction(undefined);setRevision(v=>v+1);setMessage("Đã lưu lịch nhập hàng. Tạo kế hoạch mới để áp dụng thay đổi.");}}/>}
    </>}
  </>;
}
