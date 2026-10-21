import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from '../App';
import { PRIMARY_DATASET } from '../api';

// Component fixtures exercise UI behavior, not real-data or browser acceptance.
const dataset = {
  id: PRIMARY_DATASET,
  name: 'Fixture microscopy dataset',
  source_url: 'https://zenodo.org/records/7660424',
  doi: '10.5281/zenodo.7660424',
  license: 'CC-BY-4.0',
  biology_domain: 'drosophila_embryo_in_vivo_laser_wound',
  local_available: true,
  sequence_count: 2,
  frame_count: 6,
  annotation_type: 'skeletonized_wound_boundary',
  model_status: 'untrained',
};
const sequence = {
  id: 'WH01',
  dataset_id: PRIMARY_DATASET,
  frame_count: 3,
  width: 128,
  height: 128,
  project_split: 'train',
  official_split: null,
  qc_valid_count: 2,
};
const second = { ...sequence, id: 'Test01', project_split: 'test' };
const frames = [0, 1, 2].map((i) => ({
  frame_index: i,
  timestamp_min: null,
  qc_valid: i !== 2,
  touches_border: i === 2,
}));

function mockService(fail = false, dimensions = { width: 128, height: 128 }) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const path = String(input);
    if (fail)
      return new Response(JSON.stringify({ error: { message: '本地缓存不可用' } }), {
        status: 503,
      });
    const payload = path.endsWith('/datasets')
      ? { items: [dataset] }
      : path.includes('/sequences?')
        ? { items: [sequence, second] }
        : { ...sequence, ...dimensions, id: path.split('/').pop(), frames };
    return new Response(JSON.stringify({ schema_version: '1', ...payload }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  });
}
function open(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// jsdom has no layout engine; drive actual observer notifications with measured
// content-box sizes. Real browser checks cover CSS bounds and scrolling.
function mockViewportResize() {
  let callback: ResizeObserverCallback;
  const disconnect = vi.fn();
  vi.stubGlobal(
    'ResizeObserver',
    class {
      constructor(onResize: ResizeObserverCallback) {
        callback = onResize;
      }
      observe() {}
      disconnect = disconnect;
    },
  );
  return (width: number, height: number) =>
    act(() => {
      callback([{ contentRect: { width, height } } as ResizeObserverEntry], {} as ResizeObserver);
    });
}

describe('archive component workflow', () => {
  it('filters real metadata records by search and project split, then restores empty search', async () => {
    mockService();
    open('/datasets');
    await screen.findByRole('link', { name: 'WH01' });
    const user = userEvent.setup();
    await user.selectOptions(screen.getByRole('combobox', { name: '本项目划分' }), 'test');
    expect(screen.queryByRole('link', { name: 'WH01' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Test01' })).toBeInTheDocument();
    await user.type(screen.getByRole('textbox', { name: '搜索序列' }), 'missing');
    expect(screen.getByText('没有匹配的序列')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '清除筛选' }));
    expect(screen.getByRole('link', { name: 'WH01' })).toBeInTheDocument();
    expect(screen.getAllByText('未知')).toHaveLength(2);
  });

  it('shows request errors and retries explicitly', async () => {
    const fetchMock = mockService(true);
    open('/datasets');
    expect(await screen.findByRole('alert')).toHaveTextContent('本地缓存不可用');
    fetchMock.mockRestore();
    mockService();
    await userEvent.click(screen.getByRole('button', { name: '重新读取' }));
    expect(await screen.findByRole('link', { name: 'WH01' })).toBeInTheDocument();
  });
});

describe('studio component workflow', () => {
  it('fits the measured canvas, keeps manual zoom on resize and restores fit with scroll reset', async () => {
    const resize = mockViewportResize();
    mockService();
    open('/studio/WH01');
    const image = await screen.findByRole('img', { hidden: true });
    const viewport = screen.getByLabelText('影像画布，方向键逐帧，空格播放，Home和End跳转首尾');
    const fit = screen.getByRole('button', { name: '适合画布' });
    resize(600, 220);
    expect(image).toHaveStyle({ width: '218.88px', height: '218.88px' });
    expect(viewport).toHaveAttribute('data-view-mode', 'fit');
    expect(fit).toHaveAttribute('aria-pressed', 'true');

    fireEvent.change(screen.getByRole('slider', { name: '画布缩放' }), { target: { value: '8' } });
    expect(image).toHaveStyle({ width: '1024px', height: '1024px' });
    resize(360, 160);
    expect(image).toHaveStyle({ width: '1024px', height: '1024px' });
    expect(viewport).toHaveAttribute('data-view-mode', 'manual');
    viewport.scrollTop = 140;
    viewport.scrollLeft = 90;
    await userEvent.click(fit);
    expect(image).toHaveStyle({ width: '160px', height: '160px' });
    expect(viewport.scrollTop).toBe(0);
    expect(viewport.scrollLeft).toBe(0);
    resize(360, 128);
    expect(image).toHaveStyle({ width: '128px', height: '128px' });
  });

  it('fits either dimension without stretching and ignores hidden zero-size measurements', async () => {
    const resize = mockViewportResize();
    mockService(false, { width: 128, height: 256 });
    open('/studio/WH01');
    const image = await screen.findByRole('img', { hidden: true });
    resize(300, 200);
    expect(image).toHaveStyle({ width: '99.84px', height: '199.68px' });
    resize(0, 0);
    expect(image).toHaveStyle({ width: '99.84px', height: '199.68px' });
    resize(64, 400);
    expect(image).toHaveStyle({ width: '64px', height: '128px' });
    fireEvent.change(screen.getByRole('slider', { name: '画布缩放' }), { target: { value: '2' } });
    expect(image).toHaveStyle({ width: '256px', height: '512px' });
  });

  it('supports stepping, keyboard bounds, source layers and visible failed QC', async () => {
    mockService();
    open('/studio/WH01');
    await screen.findByRole('slider', { name: '选择帧' });
    const user = userEvent.setup();
    expect(screen.getByRole('button', { name: '上一帧' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: '下一帧' }));
    expect(screen.getByRole('slider', { name: '选择帧' })).toHaveValue('1');
    const viewport = screen.getByLabelText('影像画布，方向键逐帧，空格播放，Home和End跳转首尾');
    fireEvent.keyDown(viewport, { key: 'End' });
    expect(screen.getByRole('slider', { name: '选择帧' })).toHaveValue('2');
    expect(screen.getByRole('button', { name: '下一帧' })).toBeDisabled();
    expect(screen.getByText('轮廓 QC 未通过')).toBeInTheDocument();
    expect(screen.getByText('是 · 不用于训练窗口')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /原始注释/ }));
    expect(screen.getByRole('img', { hidden: true })).toHaveAttribute(
      'src',
      '/api/v1/sequences/WH01/frames/2?layer=annotation',
    );
    expect(screen.getByText('帧时间').nextSibling).toHaveTextContent('未核实');
    fireEvent.keyDown(viewport, { key: 'Home' });
    expect(screen.getByRole('slider', { name: '选择帧' })).toHaveValue('0');
  });

  it('advances user-started playback and resets on a different source sequence', async () => {
    mockService();
    open('/studio/WH01');
    const play = await screen.findByRole('button', { name: '播放' });
    await userEvent.click(play);
    await waitFor(() => expect(screen.getByRole('slider', { name: '选择帧' })).toHaveValue('1'), {
      timeout: 1000,
    });
    await userEvent.click(screen.getByRole('link', { name: /Test01/ }));
    await screen.findByRole('heading', { name: 'Test01' });
    expect(screen.getByRole('slider', { name: '选择帧' })).toHaveValue('0');
    expect(screen.getByRole('button', { name: '播放' })).toBeInTheDocument();
  });

  it('reports image failures and allows a scoped frame retry', async () => {
    mockService();
    open('/studio/WH01');
    const image = await screen.findByRole('img', { hidden: true });
    fireEvent.error(image);
    expect(screen.getByRole('alert')).toHaveTextContent('影像读取失败');
    await userEvent.click(screen.getByRole('button', { name: '重新读取此帧' }));
    expect(image).toHaveAttribute('src', '/api/v1/sequences/WH01/frames/0?layer=overlay&retry=1');
    fireEvent.load(image);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
