import {cleanup,render,screen,fireEvent,waitFor} from '@testing-library/react';
import {afterEach,it,expect,vi} from 'vitest';
import {ReceiptQr} from '../src/operations/ReceiptQr';
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it('only fills a receipt after matching its current version, without posting stock',async()=>{
  const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,status:200,json:async()=>({version:2,external_ref:'QR-1',lines:[{order_line_id:3,quantity:4}]})} as Response);
  const apply=vi.fn();render(<ReceiptQr orderId={1} version={2} getBody={()=>({})} onApply={apply}/>);
  fireEvent.click(screen.getByText('Nhận lô SIM vật lý bằng QR'));
  fireEvent.change(screen.getByLabelText('Nội dung QR phiếu giao'),{target:{value:'qr-text'}});
  fireEvent.click(screen.getByRole('button',{name:'Đọc phiếu QR'}));
  await waitFor(()=>expect(apply).toHaveBeenCalledOnce());
  expect(String(fetch.mock.calls[0][0])).toMatch(/receipt-qr\/preview$/);
  expect(fetch).toHaveBeenCalledOnce();
});
it('does not silently update a stale form version from the QR preview',async()=>{
  vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,status:200,json:async()=>({version:9,external_ref:'QR',lines:[]})} as Response);
  const apply=vi.fn();render(<ReceiptQr orderId={1} version={2} getBody={()=>({})} onApply={apply}/>);
  fireEvent.click(screen.getByText('Nhận lô SIM vật lý bằng QR'));
  fireEvent.change(screen.getByLabelText('Nội dung QR phiếu giao'),{target:{value:'qr-text'}});
  fireEvent.click(screen.getByRole('button',{name:'Đọc phiếu QR'}));
  expect(await screen.findByText(/Đơn đã thay đổi/)).toBeVisible();expect(apply).not.toHaveBeenCalled();
});
