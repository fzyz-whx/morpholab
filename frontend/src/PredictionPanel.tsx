import { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { request } from './api';
import type { SequenceDetail } from './api';
import { QueryState } from './components';
import {
  isActiveJob,
  jobStatusLabels,
  postPrediction,
  useExperiments,
  useModels,
} from './prediction-api';
import type {
  PredictedFrame,
  PredictionJob,
  PredictionRequest,
  PredictionResult,
} from './prediction-api';

export default function PredictionPanel({
  sequence,
  frame,
  onResult,
  onClear,
}: {
  sequence: SequenceDetail;
  frame: number;
  onResult: (result: PredictionResult) => void;
  onClear: () => void;
}) {
  const models = useModels();
  const health = useQuery({
    queryKey: ['health'],
    queryFn: ({ signal }) => request<{ worker_ready: boolean }>('/health', signal),
    refetchInterval: 3000,
  });
  const experiments = useExperiments();
  const client = useQueryClient();
  const [modelId, setModelId] = useState('');
  const [observations, setObservations] = useState(4);
  const [horizon, setHorizon] = useState(12);
  const [start, setStart] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);
  const delivered = useRef<string | null>(null);
  const selectedModel =
    models.data?.find((model) => model.id === modelId) ??
    models.data?.find((model) => model.available);
  const job = useQuery({
    queryKey: ['job', jobId],
    enabled: jobId !== null,
    queryFn: async ({ signal }) =>
      (await request<{ job: PredictionJob }>(`/jobs/${encodeURIComponent(jobId!)}`, signal)).job,
    refetchInterval: (query) => (isActiveJob(query.state.data?.status) ? 700 : false),
  });
  const result = useQuery({
    queryKey: ['prediction-result', jobId],
    enabled: !!jobId && job.data?.status === 'succeeded',
    queryFn: ({ signal }) =>
      request<PredictionResult>(`/jobs/${encodeURIComponent(jobId!)}/result`, signal),
  });
  useEffect(() => {
    if (result.data && delivered.current !== result.data.job_id) {
      delivered.current = result.data.job_id;
      onResult(result.data);
      void client.invalidateQueries({ queryKey: ['experiments'] });
    }
  }, [result.data, onResult, client]);
  const submit = useMutation({
    mutationFn: (body: PredictionRequest) =>
      postPrediction<{ job: PredictionJob }>('/experiments/predict', body),
    onSuccess: ({ job: created }) => {
      client.setQueryData(['job', created.id], created);
      setJobId(created.id);
      void client.invalidateQueries({ queryKey: ['experiments'] });
    },
  });
  const cancel = useMutation({
    mutationFn: () =>
      postPrediction<{ job: PredictionJob }>(`/jobs/${encodeURIComponent(jobId!)}/cancel`),
    onSuccess: ({ job: updated }) => {
      client.setQueryData(['job', updated.id], updated);
      void client.invalidateQueries({ queryKey: ['experiments'] });
    },
  });
  const busy = submit.isPending || isActiveJob(job.data?.status);
  const validWindow = start >= 0 && start + observations + horizon <= sequence.frame_count;
  const history =
    experiments.data?.filter((item) => item.request.sequence_id === sequence.id) ?? [];
  const error = submit.error ?? cancel.error ?? job.error ?? result.error;
  return (
    <section className="prediction-panel" aria-label="预测实验设置">
      <span className="eyebrow prediction-ink">PREDICTION / 形态推理</span>
      <h2>从观测到未来轮廓</h2>
      <p className="panel-note">仅预测工作网格上的形态；灰度影像始终来自真实原帧。</p>
      {health.data?.worker_ready === false && (
        <p className="window-warning" role="status">
          推理worker未就绪。新任务会保留排队，请用本地启动命令恢复worker。
        </p>
      )}
      <QueryState
        pending={models.isPending}
        error={models.error}
        retry={() => {
          void models.refetch();
        }}
      >
        <form
          className="prediction-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (!selectedModel || !validWindow || busy) return;
            onClear();
            submit.mutate({
              dataset_id: sequence.dataset_id,
              sequence_id: sequence.id,
              model_id: selectedModel.id,
              observation_start: start,
              observations,
              horizon,
            });
          }}
        >
          <label>
            模型
            <select
              aria-label="预测模型"
              value={selectedModel?.id ?? ''}
              disabled={busy}
              onChange={(event) => setModelId(event.target.value)}
            >
              {!selectedModel && <option value="">没有可用模型</option>}
              {models.data?.map((model) => (
                <option key={model.id} value={model.id} disabled={!model.available}>
                  {model.label}
                  {!model.available ? ' · 不可用' : ''}
                </option>
              ))}
            </select>
          </label>
          {selectedModel && (
            <p className="model-selection-note">
              {selectedModel.trained
                ? `已训练 · seed ${selectedModel.seed ?? '未知'} · validation 选择`
                : '经典基线 · 无训练权重'}
            </p>
          )}
          <div className="prediction-fields">
            <label>
              观测帧数
              <select
                aria-label="观测帧数"
                value={observations}
                disabled={busy}
                onChange={(event) => setObservations(Number(event.target.value))}
              >
                {[2, 4, 8].map((n) => (
                  <option key={n} value={n}>
                    {n} frames
                  </option>
                ))}
              </select>
            </label>
            <label>
              预测步数
              <input
                aria-label="预测步数"
                type="number"
                min={1}
                max={24}
                value={horizon}
                disabled={busy}
                onChange={(event) =>
                  setHorizon(Math.max(1, Math.min(24, Number(event.target.value) || 1)))
                }
              />
            </label>
          </div>
          <label>
            观测起点
            <input
              aria-label="观测起点"
              type="number"
              min={0}
              max={sequence.frame_count - 1}
              value={start}
              disabled={busy}
              onChange={(event) => setStart(Math.max(0, Number(event.target.value) || 0))}
            />
          </label>
          <button
            type="button"
            className="text-button"
            disabled={busy}
            onClick={() => setStart(frame)}
          >
            使用当前帧 F{String(frame).padStart(3, '0')}
          </button>
          <p className={validWindow ? 'panel-note mono' : 'window-warning'}>
            {validWindow
              ? `历史 F${start}–${start + observations - 1} → 预测 F${start + observations}–${start + observations + horizon - 1}`
              : '窗口超出序列：请减少起点、观测数或预测步数。'}
          </p>
          <button
            type="submit"
            className="predict-submit"
            disabled={busy || !selectedModel?.available || !validWindow}
          >
            {submit.isPending ? '正在提交…' : '提交预测实验'}
          </button>
        </form>
      </QueryState>
      {job.data && (
        <div
          className="job-state"
          role="status"
          aria-live="polite"
          data-job-status={job.data.status}
        >
          <span className="eyebrow">{job.data.status.toUpperCase()}</span>
          <strong>{jobStatusLabels[job.data.status]}</strong>
          <code>{job.data.id}</code>
          {job.data.cancel_requested && isActiveJob(job.data.status) && (
            <p>已请求取消，等待计算任务确认。</p>
          )}
          {isActiveJob(job.data.status) && (
            <button
              type="button"
              disabled={cancel.isPending || job.data.cancel_requested}
              onClick={() => cancel.mutate()}
            >
              取消实验
            </button>
          )}
          {job.data.error && (
            <p role="alert">
              {typeof job.data.error === 'string'
                ? job.data.error
                : (job.data.error.message ?? '任务失败，未提供细节。')}
            </p>
          )}
        </div>
      )}
      {error && (
        <div className="prediction-error" role="alert">
          {error.message}
          <button
            onClick={() => {
              if (job.error) void job.refetch();
              if (result.error) void result.refetch();
              submit.reset();
              cancel.reset();
            }}
          >
            重试读取 / 清除错误
          </button>
        </div>
      )}
      {result.isFetching && <p role="status">正在读取预测结果…</p>}
      <details className="experiment-history">
        <summary>
          实验历史 <span className="mono">{history.length}</span>
        </summary>
        {experiments.isPending && <p role="status">正在读取历史…</p>}
        {experiments.error && (
          <p role="alert">
            {experiments.error.message}
            <button
              onClick={() => {
                void experiments.refetch();
              }}
            >
              重试历史
            </button>
          </p>
        )}
        {!experiments.isPending && !experiments.error && history.length === 0 && (
          <p>此序列暂无实验记录。</p>
        )}
        <ul>
          {history.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  onClear();
                  const cached = client.getQueryData<PredictionResult>([
                    'prediction-result',
                    item.id,
                  ]);
                  delivered.current = cached?.job_id ?? null;
                  setJobId(item.id);
                  if (cached) onResult(cached);
                }}
              >
                <span>{item.request.model_id}</span>
                <span className="mono">
                  L{item.request.observations} / H{item.request.horizon} ·{' '}
                  {jobStatusLabels[item.status]}
                </span>
                <time dateTime={item.created_at_utc}>{item.created_at_utc}</time>
              </button>
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}

const metricLabels = {
  iou: 'IoU · 派生区域',
  dice: 'Dice · 派生区域',
  area_mae: '面积 MAE · grid px²',
  signed_area_error: '有符号面积误差 · grid px²',
  mean_boundary_distance: '平均边界距离 · grid px',
  hausdorff95: 'HD95 · grid px',
} as const;
export function PredictionMetrics({
  result,
  current,
}: {
  result: PredictionResult;
  current?: PredictedFrame;
}) {
  return (
    <section className="prediction-metrics" aria-label="预测指标与溯源">
      <span className="eyebrow prediction-ink">LEAD METRICS</span>
      {current ? (
        <>
          <h3>
            Lead {current.lead} / F{current.source_frame_index}
          </h3>
          <p className="panel-note">
            预测面积 {current.region_area} grid px²；{result.grid.width} × {result.grid.height}{' '}
            工作网格。
          </p>
          {current.metrics && current.target_valid ? (
            <dl>
              {Object.entries(metricLabels).map(([key, label]) => (
                <div key={key}>
                  <dt>{label}</dt>
                  <dd className="mono">
                    {metricNumber(current.metrics![key as keyof typeof metricLabels])}
                  </dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="window-warning">此帧没有有效派生目标，指标未评估。</p>
          )}
        </>
      ) : (
        <p className="panel-note">当前帧在预测范围外，未显示预测轮廓。</p>
      )}
      <details open className="prediction-curves">
        <summary>预测过程 · 面积与边界</summary>
        <LeadCurve
          label="区域面积 · grid px²"
          series={[
            {
              label: 'PREDICTION',
              color: '#E2B875',
              values: result.frames.map((f) => f.region_area),
            },
            {
              label: 'DERIVED TARGET',
              color: '#D4DCA5',
              values: result.frames.map((f) =>
                f.metrics?.signed_area_error == null
                  ? null
                  : f.region_area - f.metrics.signed_area_error,
              ),
            },
          ]}
        />
        <LeadCurve
          label="平均边界距离 · grid px"
          series={[
            {
              label: 'PREDICTION vs TARGET',
              color: '#D795AB',
              values: result.frames.map((f) => f.metrics?.mean_boundary_distance ?? null),
            },
          ]}
        />
        <p className="panel-note">横轴为 lead；无有效派生目标的帧不连线、不填补指标。</p>
      </details>
      <details>
        <summary>实验溯源</summary>
        <dl className="provenance-list">
          <div>
            <dt>Job</dt>
            <dd>{result.job_id}</dd>
          </div>
          <div>
            <dt>模型</dt>
            <dd>{result.request.model_id}</dd>
          </div>
          <div>
            <dt>Checkpoint SHA256</dt>
            <dd>{result.model.checkpoint_sha256 ?? '无训练权重 / 未提供'}</dd>
          </div>
          <div>
            <dt>源 NPZ SHA256</dt>
            <dd>{result.source.npz_sha256 ?? '未提供'}</dd>
          </div>
          <div>
            <dt>Manifest SHA256</dt>
            <dd>{result.source.manifest_sha256 ?? '未提供'}</dd>
          </div>
          <div>
            <dt>Archive SHA256</dt>
            <dd>{result.source.archive_sha256 ?? '未提供'}</dd>
          </div>
          <div>
            <dt>数据/划分</dt>
            <dd>
              {result.source.source_id} / {result.source.sequence_id} /{' '}
              {result.source.project_split ?? '未知'}
            </dd>
          </div>
        </dl>
      </details>
    </section>
  );
}
function LeadCurve({
  label,
  series,
}: {
  label: string;
  series: {
    label: string;
    color: string;
    values: (number | null)[];
  }[];
}) {
  const values = series.flatMap((s) => s.values.filter((v): v is number => v != null));
  if (!values.length) return <p>{label}：未评估</p>;
  const max = Math.max(1, ...values) * 1.1;
  const count = Math.max(...series.map((s) => s.values.length));
  const x = (i: number) => 30 + (i / Math.max(1, count - 1)) * 210;
  const y = (v: number) => 100 - (v / max) * 75;
  return (
    <figure className="lead-curve">
      <figcaption>{label}</figcaption>
      <svg role="img" aria-label={`${label}随预测lead变化`} viewBox="0 0 260 125">
        <line x1="30" x2="240" y1="100" y2="100" stroke="#42515a" />
        <text x="3" y="30">
          {Math.round(max)}
        </text>
        <text x="15" y="103">
          0
        </text>
        <text x="30" y="119">
          1
        </text>
        <text x="225" y="119">
          {count}
        </text>
        {series.map((s) => (
          <g key={s.label}>
            {s.values.map(
              (v, i) =>
                v != null && (
                  <g key={i}>
                    {i > 0 && s.values[i - 1] != null && (
                      <line
                        x1={x(i - 1)}
                        x2={x(i)}
                        y1={y(s.values[i - 1]!)}
                        y2={y(v)}
                        stroke={s.color}
                      />
                    )}
                    <circle cx={x(i)} cy={y(v)} r="1.8" fill={s.color}>
                      <title>
                        {s.label} lead {i + 1}: {v.toFixed(4)}
                      </title>
                    </circle>
                  </g>
                ),
            )}
          </g>
        ))}
      </svg>
      <div>
        {series.map((s) => (
          <span key={s.label} style={{ color: s.color }}>
            {s.label}{' '}
          </span>
        ))}
      </div>
    </figure>
  );
}

function metricNumber(value: number | null) {
  return value == null || !Number.isFinite(value) ? '未评估' : value.toFixed(4);
}
