import {cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import {ScenarioItemPicker} from '../src/components/configuration/ScenarioItemPicker';
import {ScenarioEditor} from '../src/components/configuration/ScenarioEditor';
const page=(items:unknown[],total=items.length)=>({items,total,page:1,page_size:100});
const product={id:11,sku:'SYN',carrier:'Carrier A',product_type:'eSIM',city:'City A',destination_country:'Market A'};
const reply=(data:unknown,ok=true)=>Promise.resolve({ok,status:ok?200:503,json:async()=>data} as Response);
afterEach(()=>{cleanup();vi.restoreAllMocks();});

it('opens every add button without choosing a warehouse and cancelling leaves the draft untouched',async()=>{
  const saved=vi.fn();vi.spyOn(globalThis,'fetch').mockResolvedValue({ok:true,json:async()=>page([])} as Response);
  render(<ScenarioEditor onSaved={saved} onRefresh={()=>{}} onDirty={()=>{}} onBusy={()=>{}} />);
  expect(screen.queryByLabelText('Kho danh mục để chọn mặt hàng')).toBeNull();
  for(const name of ['＋ Điều chỉnh mặt hàng','＋ Lô đang về','＋ Ngừng nhập nội bộ','＋ Nhà cung cấp ngừng dịch vụ']) {
    const add=screen.getByRole('button',{name});expect(add).toBeEnabled();fireEvent.click(add);
    expect(screen.getByRole('dialog')).toBeVisible();
    fireEvent.keyDown(document,{key:'Escape'});await waitFor(()=>expect(screen.queryByRole('dialog')).toBeNull());
  }
  expect(saved).not.toHaveBeenCalled();
  expect(screen.queryByRole('button',{name:'Xóa lịch 1'})).toBeNull();
});

it('loads all carrier product pages, groups supplier products and keeps already-selected members disabled',async()=>{
  const choose=vi.fn(),reads:string[]=[];
  vi.spyOn(globalThis,'fetch').mockImplementation(input=>{
    const url=new URL(String(input),location.origin);reads.push(url.pathname+url.search);
    if(url.pathname.endsWith('/suppliers'))return reply(page([{id:1,carrier:'Carrier A'},{id:2,carrier:'Carrier B'}]));
    if(url.searchParams.get('page')==='2')return reply(page([{...product,id:111,city:'Other City'},{...product,id:112,sku:'SECOND'}],102));
    return reply(page(Array.from({length:100},(_,i)=>({...product,id:i+1})),102));
  });
  render(<ScenarioItemPicker title="Pick" productWide excludedIds={[111]} onChoose={choose} onClose={()=>{}} />);
  expect(reads.some(path=>path.includes('/products'))).toBe(false);
  await screen.findByRole('option',{name:'Carrier A'});fireEvent.change(screen.getByLabelText('Nhà mạng'),{target:{value:'Carrier A'}});
  expect(await screen.findByRole('button',{name:'Chọn SYN eSIM'})).toBeDisabled();
  fireEvent.click(screen.getByRole('button',{name:'Chọn SECOND eSIM'}));expect(choose).toHaveBeenCalledWith(expect.objectContaining({id:112}));
  expect(reads.some(path=>path.includes('page=2'))).toBe(true);expect(reads.every(path=>!path.includes('warehouse_id'))).toBe(true);
});

it('keeps search and type within the selected carrier and never shows stale carrier results',async()=>{
  const reads:string[]=[];
  vi.spyOn(globalThis,'fetch').mockImplementation(input=>{
    const url=new URL(String(input),location.origin);reads.push(url.search);
    if(url.pathname.endsWith('/suppliers'))return reply(page([{id:1,carrier:'Carrier A'},{id:2,carrier:'Carrier B'}]));
    if(url.searchParams.get('carrier')==='Carrier B')return new Promise(()=>{});
    return reply(page([product]));
  });
  render(<ScenarioItemPicker title="Pick" onChoose={()=>{}} onClose={()=>{}} />);
  await screen.findByRole('option',{name:'Carrier A'});fireEvent.change(screen.getByLabelText('Nhà mạng'),{target:{value:'Carrier A'}});
  await screen.findByRole('button',{name:'Chọn SYN eSIM tại City A'});
  fireEvent.change(screen.getByLabelText('Tìm mã SKU'),{target:{value:'SYN'}});
  fireEvent.change(screen.getByLabelText('Loại sản phẩm'),{target:{value:'eSIM'}});
  await waitFor(()=>expect(reads.some(path=>path.includes('carrier=Carrier+A')&&path.includes('search=SYN')&&path.includes('product_type=eSIM'))).toBe(true));
  fireEvent.change(screen.getByLabelText('Nhà mạng'),{target:{value:'Carrier B'}});
  expect(screen.queryByRole('button',{name:'Chọn SYN eSIM tại City A'})).toBeNull();
});

it('keeps the picker open on read errors and allows retry or cancellation',async()=>{
  let failed=true;const close=vi.fn();
  vi.spyOn(globalThis,'fetch').mockImplementation(input=>String(input).includes('/suppliers') ? reply(page([{id:1,carrier:'Carrier A'}])) : failed ? reply({error:{code:'database_unavailable',message:'Temporarily unavailable'}},false) : reply(page([product])));
  render(<ScenarioItemPicker title="Pick" onChoose={()=>{}} onClose={close} />);
  await screen.findByRole('option',{name:'Carrier A'});fireEvent.change(screen.getByLabelText('Nhà mạng'),{target:{value:'Carrier A'}});
  await screen.findByRole('alert');failed=false;fireEvent.click(within(screen.getByRole('alert')).getByRole('button',{name:'Thử tải lại'}));
  await screen.findByRole('button',{name:'Chọn SYN eSIM tại City A'});
  fireEvent.click(screen.getByRole('button',{name:'Hủy chọn'}));expect(close).toHaveBeenCalledOnce();
});
