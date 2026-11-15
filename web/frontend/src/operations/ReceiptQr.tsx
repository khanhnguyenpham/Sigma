import {useState} from 'react';
import {api} from '../services/http';
interface Preview {version:number;external_ref:string;lines:{order_line_id:number;quantity:number}[]}
export function ReceiptQr({orderId,version,getBody,onApply,onBusy}:{orderId:number;version:number;getBody:()=>unknown;onApply:(result:Preview)=>void;onBusy?:(busy:boolean)=>void}) {
  const [text,setText]=useState(''),[image,setImage]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
  async function generate() {
    const body=getBody();if(!body)return;
    setBusy(true);onBusy?.(true);setError('');
    try {const result=await api<{payload:string;image:string}>(`/operations/orders/${orderId}/receipt-qr`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});setText(result.payload);setImage(result.image);}
    catch(failure){setError((failure as Error).message);}finally{setBusy(false);onBusy?.(false);}
  }
  async function scan() {
    setBusy(true);onBusy?.(true);setError('');
    try {const result=await api<Preview>(`/operations/orders/${orderId}/receipt-qr/preview`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({payload:text})});
      if(result.version!==version){setError('Đơn đã thay đổi. Đóng form và mở lại để đối chiếu.');return;}onApply(result);
    }catch(failure){setError((failure as Error).message);}finally{setBusy(false);onBusy?.(false);}
  }
  return <details className="ops-qr"><summary>Nhận lô SIM vật lý bằng QR</summary><p>Một QR cho một phiếu giao. Máy quét QR dạng bàn phím có thể điền mã bên dưới; quét xong vẫn cần đối chiếu số thực nhận và bấm Ghi nhận nhập kho.</p>
    <label>Nội dung QR phiếu giao<textarea aria-label="Nội dung QR phiếu giao" maxLength={4096} rows={3} value={text} onChange={event=>{setText(event.target.value);setImage('');}} onKeyDown={event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();if(text&&!busy)void scan();}}}/></label>
    <div className="ops-actions"><button type="button" disabled={busy||!text} onClick={()=>void scan()}>Đọc phiếu QR</button><button type="button" disabled={busy} onClick={()=>void generate()}>Tạo QR từ phiếu đang nhập</button></div>
    {error&&<p role="alert" className="notice error">{error}</p>}{image&&<img src={image} alt="QR phiếu giao lô SIM vật lý" style={{maxWidth:'100%',width:280}}/>}
  </details>;
}
