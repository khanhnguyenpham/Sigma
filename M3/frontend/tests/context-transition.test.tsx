import {cleanup,render,screen} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import { useResource } from "../src/hooks/useResource";
afterEach(()=>{cleanup();vi.restoreAllMocks()});
it('never commits old-run values under a new request context, including before effects',async()=>{
 vi.spyOn(globalThis,'fetch').mockImplementation((url)=>String(url).endsWith('/old')?Promise.resolve({ok:true,json:async()=>({value:'old-result'})} as Response):new Promise(()=>{}));
 let renders:(string|undefined)[]=[];
 function Probe({path}:{path:string}){const result=useResource<{value:string}>(path);renders.push(result.data?.value);return <div>{result.data?.value??'waiting'}</div>}
 const view=render(<Probe path="/old"/>);await screen.findByText('old-result');renders=[];
 view.rerender(<Probe path="/new"/>);expect(renders).not.toContain('old-result');expect(screen.getByText('waiting')).toBeVisible();
});
