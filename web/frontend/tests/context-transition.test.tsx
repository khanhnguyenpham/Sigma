import {act,cleanup,render,renderHook,screen,waitFor} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import { useResource } from "../src/hooks/useResource";
import { useAppContext } from "../src/hooks/useAppContext";
afterEach(()=>{cleanup();vi.restoreAllMocks()});
it('never commits old-run values under a new request context, including before effects',async()=>{
 vi.spyOn(globalThis,'fetch').mockImplementation((url)=>String(url).endsWith('/old')?Promise.resolve({ok:true,json:async()=>({value:'old-result'})} as Response):new Promise(()=>{}));
 let renders:(string|undefined)[]=[];
 function Probe({path}:{path:string}){const result=useResource<{value:string}>(path);renders.push(result.data?.value);return <div>{result.data?.value??'waiting'}</div>}
 const view=render(<Probe path="/old"/>);await screen.findByText('old-result');renders=[];
 view.rerender(<Probe path="/new"/>);expect(renders).not.toContain('old-result');expect(screen.getByText('waiting')).toBeVisible();
});

it('keeps an explicitly cleared simulation date after the selected run recovers from a fetch error',async()=>{
 const previous=location.href;
 history.replaceState(null,'','?run_id=plan&origin=2025-10-31#product');
 let failing=false;
 vi.spyOn(globalThis,'fetch').mockImplementation((url)=>{
  const runs=String(url).includes('/runs?');
  const failed=runs&&failing;
  return Promise.resolve({ok:!failed,status:failed?503:200,json:async()=>failed?{error:{code:'temporarily_unavailable',message:'Retry'}}:{items:runs?[{id:'plan',kind:'stock_projection',status:'complete',as_of_date:'2025-10-31'}]:[],total:runs?1:0}} as Response);
 });
 try {
  const view=renderHook(()=>useAppContext());
  await waitFor(()=>expect(view.result.current.run?.id).toBe('plan'));
  act(()=>view.result.current.setCtx(c=>({...c,origin:''})));
  expect(view.result.current.ctx.origin).toBe('');
  failing=true;act(()=>window.dispatchEvent(new Event('sigma:refresh')));
  await waitFor(()=>expect(view.result.current.runsResource.error).toBeDefined());
  failing=false;act(()=>window.dispatchEvent(new Event('sigma:refresh')));
  await waitFor(()=>expect(view.result.current.run?.id).toBe('plan'));
  expect(view.result.current.ctx.origin).toBe('');
  view.unmount();
 } finally { history.replaceState(null,'',previous); }
});
