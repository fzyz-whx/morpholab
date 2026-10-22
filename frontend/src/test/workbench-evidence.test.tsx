import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, it, vi } from 'vitest';
import App from '../App';
import { PRIMARY_DATASET } from '../api';
import type {
  ModelRecord,
  PredictionJob,
  PredictionRequest,
  PredictionResult,
} from '../prediction-api';

// SYNTHETIC HTTP and DOM fixtures test UI mapping and states only. They are not
// evidence of real image assets, training quality or browser acceptance.
afterEach(() => vi.restoreAllMocks());
const sequence = {
  id: 'WH01',
  dataset_id: PRIMARY_DATASET,
  frame_count: 40,
  width: 128,
  height: 128,
  project_split: 'train',
  official_split: null,
  qc_valid_count: 40,
};
const predictionRequest: PredictionRequest = {
  dataset_id: PRIMARY_DATASET,
  sequence_id: 'WH01',
  model_id: 'persistence',
  observation_start: 0,
  observations: 4,
  horizon: 12,
};
function open(path: string, research: unknown = { status: 'pending', reports: [] }) {
  const model: ModelRecord = {
    id: 'persistence',
    label: 'Persistence',
    kind: 'baseline',
    variant: null,
    seed: null,
    trained: false,
    available: true,
    checkpoint_sha256: null,
    selection: null,
  };
  const job: PredictionJob = {
    id: '00000000-0000-0000-0000-000000000001',
    status: 'succeeded',
    request: predictionRequest,
    created_at_utc: '2026-01-01T00:00:00Z',
    updated_at_utc: '2026-01-01T00:00:00Z',
    cancel_requested: false,
    error: null,
    result_available: true,
  };
  const result: PredictionResult = {
    schema_version: '1',
    provenance: 'MODEL_PREDICTION',
    dataset_id: PRIMARY_DATASET,
    model_id: 'persistence',
    run_id: null,
    created_at_utc: job.created_at_utc,
    job_id: job.id,
    status: 'succeeded',
    request: predictionRequest,
    model,
    device: 'cpu',
    precision: 'fp32',
    target_provenance: 'DERIVED_ANNOTATION',
    inference_environment: {
      deterministic: true,
      cpu_threads: 1,
      convolution_fp32_precision: 'ieee',
    },
    grid: { width: 64, height: 64, contour_coordinates: 'working-grid pixel centers' },
    source: {
      source_id: 'zenodo:7660424',
      sequence_id: 'WH01',
      npz_sha256: 'f'.repeat(64),
      manifest_sha256: 'a'.repeat(64),
      archive_sha256: 'b'.repeat(64),
      original_width: 128,
      original_height: 128,
      project_split: 'train',
    },
    frames: Array.from({ length: 12 }, (_, i) => ({
      lead: i + 1,
      source_frame_index: i + 4,
      contours: [
        [
          [0, 0],
          [63, 63],
        ],
      ],
      region_area: 200,
      target_area: 190,
      target_valid: true,
      metrics: {
        iou: 0.9,
        dice: 0.9474,
        area_mae: 10,
        signed_area_error: 10,
        mean_boundary_distance: 1,
        hausdorff95: 2,
        empty_boundary_mismatch: false,
      },
      images: {
        prediction: {
          url: `/api/v1/jobs/${job.id}/frames/${i + 1}?layer=prediction`,
          sha256: 'c'.repeat(64),
        },
        target: {
          url: `/api/v1/jobs/${job.id}/frames/${i + 1}?layer=target`,
          sha256: 'd'.repeat(64),
        },
        error: {
          url: `/api/v1/jobs/${job.id}/frames/${i + 1}?layer=error`,
          sha256: 'e'.repeat(64),
        },
      },
    })),
  };
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = String(input);
    const body = url.endsWith('/research')
      ? research
      : url.endsWith('/models')
        ? { items: [model] }
        : url.endsWith('/datasets')
          ? { items: [] }
          : url.endsWith('/experiments')
            ? { items: [] }
            : url.includes('/sequences?')
              ? { items: [sequence] }
              : url.endsWith('/result')
                ? result
                : url.includes('/jobs/') || url.endsWith('/predict')
                  ? { job }
                  : {
                      ...sequence,
                      frames: Array.from({ length: 40 }, (_, frame_index) => ({
                        frame_index,
                        qc_valid: true,
                        touches_border: false,
                        timestamp_min: null,
                      })),
                    };
    return new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } });
  });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

it('maps source pixel coordinates from actual image geometry, invalidates on zoom and clears outside bounds', async () => {
  open('/studio/WH01');
  const image = await screen.findByAltText(/WH01 第 0 帧/);
  fireEvent.load(image);
  const geometry = image.closest('.frame-geometry')!;
  let size = 256;
  vi.spyOn(geometry, 'getBoundingClientRect').mockImplementation(() => ({
    left: 200,
    top: 100,
    width: size,
    height: size,
    right: 200 + size,
    bottom: 100 + size,
    x: 200,
    y: 100,
    toJSON() {},
  }));
  const output = screen.getByLabelText('原始图像坐标');
  expect(output).toHaveTextContent('X — / Y —');
  fireEvent.mouseMove(geometry, { clientX: 328, clientY: 164 });
  expect(output).toHaveTextContent('X 064 / Y 032');
  fireEvent.mouseMove(geometry, { clientX: 456, clientY: 164 });
  expect(output).toHaveTextContent('X — / Y —');
  fireEvent.mouseMove(geometry, { clientX: 455.9, clientY: 355.9 });
  expect(output).toHaveTextContent('X 127 / Y 127');
  fireEvent.mouseLeave(geometry);
  expect(output).toHaveTextContent('X — / Y —');
  fireEvent.mouseMove(geometry, { clientX: 328, clientY: 164 });
  fireEvent.change(screen.getByRole('slider', { name: '画布缩放' }), { target: { value: '4' } });
  expect(output).toHaveTextContent('X — / Y —');
  size = 512;
  fireEvent.mouseMove(geometry, { clientX: 456, clientY: 228 });
  expect(output).toHaveTextContent('X 064 / Y 032');
  fireEvent.error(image);
  expect(output).toHaveTextContent('X — / Y —');
  fireEvent.click(screen.getByRole('button', { name: '下一帧' }));
  expect(output).toHaveTextContent('X — / Y —');
});

it('uses keyboard-accessible previous observed frame reference with original indices and scoped retry', async () => {
  open('/studio/WH01');
  const toggle = await screen.findByRole('button', { name: '前帧参照' });
  expect(toggle).toBeDisabled();
  await userEvent.click(screen.getByRole('button', { name: '下一帧' }));
  toggle.focus();
  await userEvent.keyboard('{Enter}');
  const previous = screen.getByRole('img', { name: 'WH01 前一真实观测帧 0' });
  expect(previous).toHaveAttribute('src', '/api/v1/sequences/WH01/frames/0?layer=observed');
  expect(previous.closest('figure')).toHaveTextContent('OBSERVED / 前帧参照F000');
  expect(previous.closest('.scientific-viewport')).toBeNull();
  fireEvent.error(previous);
  await userEvent.click(screen.getByRole('button', { name: '重试前帧' }));
  expect(screen.getByRole('img', { name: 'WH01 前一真实观测帧 0' })).toHaveAttribute(
    'src',
    expect.stringContaining('&retry=1'),
  );
  await userEvent.click(screen.getByRole('button', { name: '首帧' }));
  expect(toggle).toBeDisabled();
  expect(toggle).toHaveAttribute('aria-pressed', 'false');
  expect(screen.queryByRole('img', { name: /前一真实观测帧/ })).not.toBeInTheDocument();
});

it('renders backend error PNG independently of SVG contour geometry and retries only the failed asset', async () => {
  open('/studio/WH01');
  await screen.findByRole('slider', { name: '选择帧' });
  await userEvent.click(screen.getAllByRole('button', { name: '预测实验' })[0]);
  await userEvent.click(await screen.findByRole('button', { name: '提交预测实验' }));
  await waitFor(() => expect(screen.getByRole('slider', { name: '选择帧' })).toHaveValue('4'));
  fireEvent.load(screen.getByAltText(/WH01 第 4 帧/));
  await userEvent.click(screen.getByRole('button', { name: /派生区域误差/ }));
  const error = screen.getByRole('img', { name: /派生区域误差层/ });
  expect(error).toHaveAttribute(
    'src',
    '/api/v1/jobs/00000000-0000-0000-0000-000000000001/frames/1?layer=error',
  );
  const contour = screen.getByRole('img', { name: /PREDICTION Lead 1/ });
  expect(contour).toHaveAttribute('viewBox', '-0.5 -0.5 64 64');
  expect(contour.querySelectorAll('rect')).toHaveLength(0);
  expect(contour.querySelector('polyline')).toHaveAttribute('stroke-dasharray', '5 3');
  fireEvent.error(error);
  expect(screen.getByRole('alert')).toHaveTextContent('误差图加载失败');
  await userEvent.click(screen.getByRole('button', { name: '重试误差图' }));
  expect(screen.getByRole('img', { name: /派生区域误差层/ })).toHaveAttribute(
    'src',
    expect.stringContaining('&retry=1'),
  );
  expect(screen.getByRole('img', { name: /WH01 第 4 帧/ })).toHaveAttribute(
    'src',
    '/api/v1/sequences/WH01/frames/4?layer=overlay',
  );
});

it('shows public failure figures and each recorded training run/configuration without generating research data', async () => {
  const run = {
    variant: 'nca',
    seed: 17,
    completed_steps: 600,
    best_step: 500,
    best_validation_loss: 0.01234,
    elapsed_seconds: 81.5,
    parameter_count: 1024,
    best_sha256: 'fixture-weight-sha256',
    cuda_peak_allocated_bytes: 1048576,
    cpu_peak_memory_bytes: null,
    device: 'cuda',
    precision: 'fp32',
    git_sha: 'fixture-git-sha',
    config: { maximum_steps: 600, learning_rate: 0.002, loss: { dice_weight: 0.1 } },
    model_config: { hidden_channels: 64 },
    versions: { torch: 'fixture-only' },
  };
  open('/research', {
    status: 'available',
    configuration: { horizon: 24, observations: 4, stride: 12 },
    reports: [
      {
        id: 'fixture-report',
        label: 'Fixture NCA',
        model_id: 'nca',
        observations: 4,
        horizon: 24,
        seeds: [17, 29, 43],
        metrics: [{ lead: 24, n: 5, n_windows: 10, mean: { iou: 0.5 }, sample_sd: { iou: 0.1 } }],
        provenance: {
          split: 'test',
          target: 'DERIVED_ANNOTATION',
          git_sha: null,
          manifest_sha256: null,
        },
      },
    ],
    runs: [run],
    failure_cases: [
      {
        variant: 'nca',
        selection: 'SYNTHETIC fixed selection rule',
        metrics: {
          sequence_id: 'Test01',
          source_target_index: 27,
          lead: 24,
          seed: 17,
          iou: 0.1,
          dice: 0.2,
          empty_boundary_mismatch: true,
        },
        png_url: '/api/v1/research/figures/fixture.png',
        png_sha256: 'fixture-png-sha256',
      },
    ],
  });
  const runs = await screen.findByRole('region', { name: '训练运行与预算' });
  expect(runs).toHaveTextContent('1 RUNS');
  expect(runs).toHaveTextContent('600 / 600');
  expect(runs).toHaveTextContent('0.0123');
  expect(runs).toHaveTextContent('81.500');
  expect(runs).toHaveTextContent('fixture-weight-sha256');
  expect(runs).toHaveTextContent('learning_rate');
  const failures = screen.getByRole('region', { name: '真实失败案例' });
  const image = within(failures).getByRole('img', { name: /nca 真实失败案例/ });
  expect(image).toHaveAttribute('src', '/api/v1/research/figures/fixture.png');
  expect(failures).toHaveTextContent('SYNTHETIC fixed selection rule');
  expect(failures).toHaveTextContent('Test01 / F27 / Lead 24');
  expect(failures).toHaveTextContent('fixture-png-sha256');
  fireEvent.error(image);
  expect(screen.getByRole('alert')).toHaveTextContent('失败案例图未能读取');
  await userEvent.click(screen.getByRole('button', { name: '重试案例图' }));
  expect(screen.getByRole('img', { name: /nca 真实失败案例/ })).toHaveAttribute(
    'src',
    '/api/v1/research/figures/fixture.png?retry=1',
  );
});
