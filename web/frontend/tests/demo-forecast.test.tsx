import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import App from '../src/App';

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); history.replaceState(null, '', '/'); });
it('uses operational H14 without monthly UI or requests in demo', async () => {
  history.replaceState(null, '', '/?run_id=demo&origin=2025-09-30#forecast');
  vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} });
  const calls: string[] = [];
  vi.spyOn(globalThis, 'fetch').mockImplementation(async input => {
    const url = String(input); calls.push(url);
    const body = url.includes('/runs?') ? { items: [{ id: 'demo', kind: 'forecast', status: 'complete', as_of_date: '2025-09-30', result_summary: {} }], total: 1 }
      : { items: [], total: 0 };
    return { ok: true, json: async () => body } as Response;
  });
  render(<App />);
  await screen.findByRole('heading', { name: 'Dự báo tổng tuần' });
  expect(screen.queryByText(/Tổng 30/)).toBeNull();
  expect(screen.getByRole('button', { name: 'Tổng 7 ngày' })).toHaveClass('active');
  fireEvent.click(screen.getByRole('button', { name: 'Phân bổ theo ngày' }));
  await screen.findByRole('heading', { name: 'Ngày phân bổ từ tổng tuần' });
  await waitFor(() => expect(calls.some(url => url.includes('/forecasts/items?'))).toBe(true));
  expect(calls.some(url => url.includes('monthly'))).toBe(false);
});
