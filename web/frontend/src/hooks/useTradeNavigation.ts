import { useEffect, useRef } from "react";

/** Keep unsaved lifecycle forms and their modal Back entry together. */
export function useTradeNavigation(dirty:boolean,busy:boolean,onClose:()=>void,modal:boolean) {
  const current=useRef({dirty,busy,onClose,url:location.href});
  current.current={dirty,busy,onClose,url:location.href};
  const token=useRef(crypto.randomUUID()),leaving=useRef(false);
  function allowed(){return !current.current.busy && (!current.current.dirty || window.confirm("Bỏ các thay đổi chưa lưu?"));}
  function finish(){leaving.current=true;if(modal && history.state?.tradeDialog===token.current)history.back();}
  function close(){if(allowed()){finish();current.current.onClose();}}
  useEffect(()=>{
    const hash=location.hash;
    if(modal && history.state?.tradeDialog!==token.current)history.pushState({...history.state,tradeDialog:token.current},"");
    const guard=(event:Event)=>{
      if(leaving.current)return;
      if(!allowed()){
        event.preventDefault();
        if((event as CustomEvent).detail?.pop)history.pushState(null,"",current.current.url);
      }
    };
    const back=()=>{
      if(!modal || leaving.current || location.hash!==hash || history.state?.tradeDialog===token.current)return;
      if(allowed()){leaving.current=true;current.current.onClose();}
      else history.pushState({...history.state,tradeDialog:token.current},"",current.current.url);
    };
    const unload=(event:BeforeUnloadEvent)=>{if(!leaving.current && (current.current.dirty || current.current.busy)){event.preventDefault();event.returnValue="";}};
    window.addEventListener("sigma:before-navigate",guard);
    window.addEventListener("popstate",back);
    window.addEventListener("beforeunload",unload);
    return()=>{window.removeEventListener("sigma:before-navigate",guard);window.removeEventListener("popstate",back);window.removeEventListener("beforeunload",unload);};
  },[modal]);
  return {close,finish};
}
