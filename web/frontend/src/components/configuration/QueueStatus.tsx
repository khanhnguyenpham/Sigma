import {useResource} from '../../hooks/useResource';
export function QueueStatus({refresh=0}:{refresh?:number}) {
  const result=useResource<{driver:string;available:boolean;message:string}>('/operations/queue-status',false,refresh);
  if(result.data?.available!==false)return null;
  return <p className="notice error" role="alert">Bộ xử lý kế hoạch đang mất kết nối. Công việc đã gửi vẫn được lưu; bạn có thể tiếp tục xem kết quả cũ và thử lại sau.</p>;
}
