import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import PredictionPanel from '../PredictionPanel';
import { PRIMARY_DATASET } from '../api';
import type { SequenceDetail } from '../api';

// SYNTHETIC HTTP fixtures verify UI states, not model quality or real E2E.
const sequence = { id: 'WH01', dataset_id: PRIMARY_DATASET, frame_count: 40 } as SequenceDetail;
afterEach(() => vi.restoreAllMocks());

function panel(mode: 'success' | 'queued' | 'error') {
  let status = mode === 'queued' ? 'queued' : 'succeeded';
  const request = {
    dataset_id: PRIMARY_DATASET,
    sequence_id: 'WH01',
    model_id: 'nca',
    observation_start: 0,
    observations: 4,
    horizon: 12,
  };
  const job = () => ({
    id: 'synthetic-job',
    status,
    request,
    created_at_utc: '2026-01-01T00:00:00Z',
    updated_at_utc: '2026-01-01T00:00:00Z',
    cancel_requested: false,
    error: null,
    result_available: status === 'succeeded',
  });
  const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = String(input);
    let body: unknown;
    if (url.endsWith('/models'))
      body = { items: [{ id: 'nca', label: 'NCA', available: true, trained: true, seed: 17 }] };
    else if (url.endsWith('/experiments')) body = { items: [] };
    else if (url.endsWith('/predict')) {
      if (mode === 'error')
        return new Response(
          JSON.stringify({ error: { message: 'SYNTHETIC source unavailable' } }),
          { status: 503 },
        );
      expect(JSON.parse(String(init?.body))).toEqual(request);
      body = { job: job() };
    } else if (url.endsWith('/cancel')) {
      status = 'cancelled';
      body = { job: job() };
    } else if (url.endsWith('/result'))
      body = { job_id: 'synthetic-job', status: 'succeeded', request, frames: [] };
    else body = { job: job() };
    return new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } });
  });
  const onResult = vi.fn();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <PredictionPanel sequence={sequence} frame={0} onResult={onResult} onClear={vi.fn()} />
    </QueryClientProvider>,
  );
  return { fetch, onResult };
}

it('submits history parameters and loads a successful saved result', async () => {
  const { onResult } = panel('success');
  await screen.findByRole('option', { name: 'NCA' });
  await userEvent.click(screen.getByRole('button', { name: '提交预测实验' }));
  await waitFor(() => expect(onResult).toHaveBeenCalledTimes(1));
  expect(screen.getByText('已完成', { exact: true })).toBeInTheDocument();
});

it('cancels a queued job through the API and shows its terminal state', async () => {
  panel('queued');
  await screen.findByRole('option', { name: 'NCA' });
  await userEvent.click(screen.getByRole('button', { name: '提交预测实验' }));
  await userEvent.click(await screen.findByRole('button', { name: '取消实验' }));
  expect(await screen.findByText('已取消', { exact: true })).toBeInTheDocument();
});

it('shows an actual submission failure without fabricating a result', async () => {
  const { onResult } = panel('error');
  await screen.findByRole('option', { name: 'NCA' });
  await userEvent.click(screen.getByRole('button', { name: '提交预测实验' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('SYNTHETIC source unavailable');
  expect(onResult).not.toHaveBeenCalled();
});
