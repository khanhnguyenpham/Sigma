import {cleanup,render,screen} from '@testing-library/react';
import {afterEach,it,expect,vi} from 'vitest';
import {QueueStatus} from '../src/components/configuration/QueueStatus';
afterEach(()=>{cleanup();vi.restoreAllMocks();});
it('explains that a Redis outage preserves queued work instead of reporting completion',async()=>{
  vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,status:200,json:async()=>({driver:'redis',available:false,message:'Redis chưa sẵn sàng.'})} as Response);
  render(<QueueStatus/>);
  expect(await screen.findByRole('alert')).toHaveTextContent('Công việc đã gửi vẫn được lưu');
});
