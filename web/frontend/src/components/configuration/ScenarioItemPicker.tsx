import { useState } from "react";
import { createPortal } from "react-dom";
import type { Page, Row } from "../../types/api";
import { useResource } from "../../hooks/useResource";
import { useDialogFocus } from "../../hooks/useDialogFocus";
import { apiAllPages } from "../../services/http";
import { query } from "../../utils/url";
import { State } from "../ui/State";
import { Table } from "../ui/Table";
import { Pager } from "../ui/Pager";

export function ScenarioItemPicker({ title, productWide=false, excludedIds=[], onChoose, onClose }: {
  title: string; productWide?: boolean; excludedIds?: number[]; onChoose:(row:Row)=>void; onClose:()=>void;
}) {
  const [carrier,setCarrier]=useState(''),[search,setSearch]=useState(''),[type,setType]=useState(''),[page,setPage]=useState(1);
  useDialogFocus(true,onClose);
  const suppliers=useResource<Page>('/suppliers?page_size=100',false,0,apiAllPages);
  const products=useResource<Page>(carrier ? `/products?${query({carrier,search,product_type:type,page_size:100})}` : null,false,0,apiAllPages);
  const grouped=new Map<string,Row>();
  for (const row of products.data?.items ?? []) {
    const key=productWide ? JSON.stringify([row.carrier,row.sku,row.product_type]) : String(row.id);
    const previous=grouped.get(key);
    grouped.set(key,{...(previous ?? row),selected:previous?.selected===true || excludedIds.includes(Number(row.id))});
  }
  const rows=[...grouped.values()];
  return createPortal(<div className="modal-shade"><section className="modal scenario-item-picker" role="dialog" aria-modal="true" aria-labelledby="scenario-item-picker-title">
    <button type="button" className="close" aria-label="Đóng chọn mặt hàng" onClick={onClose}>×</button>
    <h2 id="scenario-item-picker-title">{title}</h2>
    <p>Chọn nhà mạng, tìm SKU và chọn loại sản phẩm. {productWide ? 'Một lựa chọn áp dụng cho cùng SKU, loại và nhà mạng trên tất cả kho.' : 'Thông tin khu vực giúp phân biệt các mặt hàng trùng mã.'}</p>
    <div className="scenario-item-filters">
      <label>Nhà mạng<select value={carrier} onChange={e=>{setCarrier(e.target.value);setPage(1);}}><option value="">Chọn nhà mạng</option>{suppliers.data?.items.map(row=><option key={String(row.id)} value={String(row.carrier)}>{String(row.carrier)}</option>)}</select></label>
      <label>Tìm mã SKU<input type="search" value={search} onChange={e=>{setSearch(e.target.value);setPage(1);}} placeholder="Nhập mã sản phẩm…" /></label>
      <label>Loại sản phẩm<select value={type} onChange={e=>{setType(e.target.value);setPage(1);}}><option value="">Tất cả loại</option><option value="eSIM">eSIM</option><option value="physical_SIM">SIM vật lý</option></select></label>
    </div>
    <State loading={suppliers.loading || products.loading} error={suppliers.error ?? products.error} />
    {!carrier && <p className="notice">Chọn nhà mạng để xem các mặt hàng.</p>}
    {carrier && !products.loading && !products.error && <>
      <State empty={!rows.length} />
      {!!rows.length && <><Table rows={rows.slice((page-1)*50,page*50)} columns={[
        {key:'sku',label:'Mã sản phẩm'}, {key:'product_type',label:'Loại'},
        ...(productWide ? [] : [{key:'city',label:'Khu vực',render:(_:unknown,row:Row)=><>{String(row.city)} · {String(row.destination_country)}</>}]),
        {key:'select',label:'',render:(_,row)=><button type="button" disabled={row.selected===true} aria-label={`Chọn ${row.sku} ${row.product_type}${productWide ? '' : ` tại ${row.city}`}`} onClick={()=>onChoose(row)}>{row.selected ? 'Đã có trong danh sách' : 'Chọn mặt hàng'}</button>},
      ]} /><Pager page={page} total={rows.length} onChange={setPage} /></>}
    </>}
    <button type="button" className="secondary" onClick={onClose}>Hủy chọn</button>
  </section></div>,document.body);
}

export function ScenarioItemField({ itemId, item, name, onChoose }: {itemId:unknown;item?:Row;name:string;onChoose:()=>void}) {
  const resource=useResource<Row>(item || !itemId ? null : `/products/${itemId}`);
  const row=item ?? resource.data;
  return <button type="button" className="scenario-item-field secondary" aria-label={`Đổi mặt hàng ${name}`} onClick={onChoose}>
    <strong>{typeof row?.sku==='string' ? row.sku : `Mặt hàng #${itemId}`}</strong>
    {typeof row?.sku==='string' && <small>{String(row.product_type)} · {String(row.carrier)} · {String(row.city)}</small>}
    <small>{resource.error ? 'Không tải được tên. Nhấn để chọn lại.' : 'Nhấn để đổi mặt hàng'}</small>
  </button>;
}
