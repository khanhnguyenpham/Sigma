import {useResource} from '../../hooks/useResource';
export function QueueStatus({refresh=0}:{refresh?:number}) {
  const result=useResource<{driver:string;available:boolean;message:string}>('/operations/queue-status',false,refresh);
  if(result.data?.available!==false)return null;
  return <p className="notice error" role="alert">{result.data.message} Chưa tự chuyển sang hàng đợi khác; bạn có thể tiếp tục xem dữ liệu đã lưu.</p>;
}
