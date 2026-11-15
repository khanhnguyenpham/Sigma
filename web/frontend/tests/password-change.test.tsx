import {cleanup,render,screen,fireEvent,waitFor} from '@testing-library/react';
import {afterEach,it,expect,vi} from 'vitest';
import {ChangePassword} from '../src/auth/ChangePassword';
afterEach(()=>{cleanup();vi.restoreAllMocks();});
function fill(confirm='Synthetic-new-password') {
  fireEvent.change(screen.getByLabelText('Mật khẩu hiện tại'),{target:{value:'Synthetic-old-password'}});
  fireEvent.change(screen.getByLabelText('Mật khẩu mới'),{target:{value:'Synthetic-new-password'}});
  fireEvent.change(screen.getByLabelText('Nhập lại mật khẩu mới'),{target:{value:confirm}});
}
it('does not send mismatched passwords',async()=>{
  const fetch=vi.spyOn(globalThis,'fetch');
  render(<ChangePassword onClose={vi.fn()}/>);fill('Synthetic-mismatch');
  fireEvent.click(screen.getByRole('button',{name:'Đổi mật khẩu'}));
  expect(await screen.findByText('Hai mật khẩu mới chưa khớp.')).toBeVisible();
  expect(fetch).not.toHaveBeenCalled();
});
it('requires login again only after a successful password change',async()=>{
  const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,status:200,json:async()=>({ok:true,login_required:true})} as Response);
  const expired=vi.fn(), close=vi.fn();window.addEventListener('sigma:unauthorized',expired);
  try {
    render(<ChangePassword onClose={close}/>);fill();fireEvent.click(screen.getByRole('button',{name:'Đổi mật khẩu'}));
    await waitFor(()=>expect(close).toHaveBeenCalledOnce());expect(expired).toHaveBeenCalledOnce();
    expect(String(fetch.mock.calls[0][0])).toMatch(/\/auth\/password$/);
  } finally {window.removeEventListener('sigma:unauthorized',expired);}
});
