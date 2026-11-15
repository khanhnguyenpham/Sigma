import { useState, type FormEvent } from "react";
import { Dialog } from "../components/ui/Dialog";
import { api } from "../services/http";

export function ChangePassword({onClose}:{onClose:()=>void}) {
  const [busy,setBusy]=useState(false),[error,setError]=useState("");
  async function submit(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form=event.currentTarget, values=new FormData(form);
    if(values.get('new_password')!==values.get('confirm_password')) {setError('Hai mật khẩu mới chưa khớp.');return;}
    setBusy(true);setError("");
    try {
      await api('/auth/password',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({current_password:values.get('current_password'),new_password:values.get('new_password')})});
      form.reset(); onClose(); window.dispatchEvent(new Event('sigma:unauthorized'));
    } catch(failure) {setError((failure as Error).message);}
    finally {setBusy(false);}
  }
  return <Dialog title="Đổi mật khẩu" onClose={onClose} busy={busy} className="operations-form-dialog">
    <form onSubmit={event=>void submit(event)}><fieldset disabled={busy}><div className="operations-form-fields">
      <p>Đổi thành công sẽ đăng xuất các phiên hiện tại. Đăng nhập lại bằng mật khẩu mới.</p>
      <label>Mật khẩu hiện tại<input name="current_password" type="password" autoComplete="current-password" required maxLength={128}/></label>
      <label>Mật khẩu mới<input name="new_password" type="password" autoComplete="new-password" required minLength={12} maxLength={128}/></label>
      <label>Nhập lại mật khẩu mới<input name="confirm_password" type="password" autoComplete="new-password" required minLength={12} maxLength={128}/></label>
      {error&&<p className="notice error" role="alert">{error}</p>}
    </div><div className="dialog-form-actions"><button type="button" onClick={onClose}>Hủy</button><button className="primary" type="submit">{busy?'Đang đổi…':'Đổi mật khẩu'}</button></div></fieldset></form>
  </Dialog>;
}
