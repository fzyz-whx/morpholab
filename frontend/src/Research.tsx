import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { request } from './api';
import { QueryState } from './components';

type MetricKey =
  | 'iou'
  | 'dice'
  | 'area_mae'
  | 'signed_area_error'
  | 'mean_boundary_distance'
  | 'hausdorff95'
  | 'empty_boundary_mismatch';
interface ResearchPoint {
  lead: number;
  n: number;
  n_windows: number;
  mean: Partial<Record<MetricKey, number | null>>;
  sample_sd: Partial<Record<MetricKey, number | null>>;
}
interface ResearchReport {
  id: string;
  label: string;
  model_id: string;
  observations: number;
  horizon: number;
  seeds: number[];
  metrics: ResearchPoint[];
  provenance: {
    split: string;
    git_sha: string | null;
    manifest_sha256: string | null;
    target: string;
  };
}
interface ResearchResponse {
  status: 'pending' | 'available';
  reports: ResearchReport[];
  configuration?: Record<string, unknown>;
  runs?: ResearchRun[];
  failure_cases?: FailureCase[];
}
interface ResearchRun {
  variant: string;
  seed: number;
  completed_steps: number;
  best_step: number;
  best_validation_loss: number | null;
  elapsed_seconds: number | null;
  parameter_count: number | null;
  best_sha256: string | null;
  cuda_peak_allocated_bytes: number | null;
  cpu_peak_memory_bytes: number | null;
  device: string;
  precision: string;
  git_sha: string | null;
  config: Record<string, unknown>;
  model_config: Record<string, unknown>;
  versions: Record<string, unknown>;
}
interface FailureCase {
  variant: string;
  selection: string;
  metrics: Partial<Record<MetricKey, number | boolean | null>> & {
    sequence_id?: string;
    source_target_index?: number;
    lead?: number;
    seed?: number | null;
  };
  png_url: string;
  png_sha256: string;
}
const metricLabels: Record<MetricKey, string> = {
  iou: 'IoU · 派生区域',
  dice: 'Dice · 派生区域',
  area_mae: '面积 MAE · grid px²',
  signed_area_error: '有符号面积误差 · grid px²',
  mean_boundary_distance: '平均边界距离 · grid px',
  hausdorff95: 'HD95 · grid px',
  empty_boundary_mismatch: '空边界不匹配率',
};
const seriesColors = ['#8ec5b5', '#91a5a8', '#b4c3e0', '#e2b875', '#d79583', '#d4dca5'];
const format = (value: number | null | undefined) =>
  value == null || !Number.isFinite(value) ? '未评估' : value.toFixed(4);

export default function Research() {
  const research = useQuery({
    queryKey: ['research'],
    queryFn: ({ signal }) => request<ResearchResponse>('/research', signal),
  });
  const [metric, setMetric] = useState<MetricKey>('iou');
  const reports = research.data?.reports ?? [];
  return (
    <main id="main" className="page research-page">
      <div className="page-kicker">
        <span>RESEARCH NOTEBOOK</span>
        <span>研究记录 / 03</span>
      </div>
      <div className="page-heading">
        <div>
          <h1>让预测接受检验。</h1>
          <p>读取已公开的冻结报告；交互推理不会重新运行研究评估。</p>
        </div>
        <Link className="text-link" to="/methods">
          标签、划分与局限 ↗
        </Link>
      </div>
      <QueryState
        pending={research.isPending}
        error={research.error}
        retry={() => {
          void research.refetch();
        }}
      >
        {research.data?.status !== 'available' || reports.length === 0 ? (
          <section className="research-pending">
            <span className="eyebrow">PENDING / 公开报告待取得</span>
            <h2>尚未取得可公开的研究报告</h2>
            <p>模型可用性与研究评估是两项证据。此处不生成替代分数或占位曲线。</p>
            <button
              onClick={() => {
                void research.refetch();
              }}
            >
              重新读取报告
            </button>
          </section>
        ) : (
          <>
            <div className="research-protocol">
              <span className="eyebrow">FROZEN REPORT / DERIVED ANNOTATION</span>
              <p>
                IoU / Dice 评价由原始轮廓推导的区域，不是人工填充真值准确度。均值、sample SD、seed
                数与序列数直接来自公开报告；seed 间变化不等于生物不确定性。
              </p>
            </div>
            <section className="research-chart-section">
              <div className="section-topline">
                <h2>误差随预测距离变化</h2>
                <label className="research-metric-control">
                  指标
                  <select
                    aria-label="研究指标"
                    value={metric}
                    onChange={(event) => setMetric(event.target.value as MetricKey)}
                  >
                    {Object.entries(metricLabels).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="research-chart-scroll">
                <ResearchChart reports={reports} metric={metric} />
              </div>
              <div className="research-legend">
                {reports.map((report, index) => (
                  <span key={report.id}>
                    <i style={{ borderColor: seriesColors[index % seriesColors.length] }} />
                    {report.label}
                  </span>
                ))}
              </div>
              <p className="panel-note">
                仅绘制报告实际提供的 lead；连接线用于阅读，未计算中间步。误差棒为报告提供的 sample
                SD，缺失时不绘制。
              </p>
            </section>
            <div className="table-scroll research-results">
              <table>
                <caption>{metricLabels[metric]} · mean ± sample SD</caption>
                <thead>
                  <tr>
                    <th>模型</th>
                    <th>观测 / 预测</th>
                    <th>Lead</th>
                    <th className="number">均值</th>
                    <th className="number">sample SD</th>
                    <th className="number">n seeds</th>
                    <th className="number">n sequences</th>
                    <th className="number">n windows</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.flatMap((report) =>
                    report.metrics
                      .filter((point) => [4, 12, 24].includes(point.lead))
                      .map((point) => (
                        <tr key={`${report.id}-${point.lead}`}>
                          <td>{report.label}</td>
                          <td className="mono">
                            L{report.observations} / H{report.horizon}
                          </td>
                          <td className="mono">{point.lead}</td>
                          <td className="number mono">{format(point.mean[metric])}</td>
                          <td className="number mono">{format(point.sample_sd?.[metric])}</td>
                          <td className="number mono">{report.seeds.length || '不适用'}</td>
                          <td className="number mono">{point.n}</td>
                          <td className="number mono">{point.n_windows}</td>
                        </tr>
                      )),
                  )}
                </tbody>
              </table>
            </div>
            <section className="research-run-section" aria-label="训练运行与预算">
              <div className="section-topline">
                <h2>运行配置与实际预算</h2>
                <span className="mono muted">{research.data.runs?.length ?? 0} RUNS</span>
              </div>
              <p className="panel-note">
                权重按最佳 validation loss
                选择；下列耗时与内存是报告记录的实际消耗，未提供的值保持未知。
              </p>
              {research.data.configuration && (
                <details className="research-config">
                  <summary>冻结评估配置</summary>
                  <Configuration values={research.data.configuration} />
                </details>
              )}
              {research.data.runs?.length ? (
                <>
                  <div className="table-scroll research-results">
                    <table>
                      <caption>训练运行 · seed、验证选择与计算预算</caption>
                      <thead>
                        <tr>
                          <th>Variant / seed</th>
                          <th className="number">完成 / 最大步数</th>
                          <th className="number">最佳 step</th>
                          <th className="number">最佳 validation loss</th>
                          <th className="number">耗时 / s</th>
                          <th className="number">参数量</th>
                          <th className="number">峰值 CUDA / MiB</th>
                        </tr>
                      </thead>
                      <tbody>
                        {research.data.runs.map((run) => (
                          <tr key={`${run.variant}-${run.seed}`}>
                            <td>
                              {run.variant}
                              <span className="run-seed mono">seed {run.seed}</span>
                            </td>
                            <td className="number mono">
                              {run.completed_steps} / {displayValue(run.config.maximum_steps)}
                            </td>
                            <td className="number mono">{run.best_step}</td>
                            <td className="number mono">{format(run.best_validation_loss)}</td>
                            <td className="number mono">
                              {run.elapsed_seconds == null
                                ? '未提供'
                                : run.elapsed_seconds.toFixed(3)}
                            </td>
                            <td className="number mono">{run.parameter_count ?? '未提供'}</td>
                            <td className="number mono">
                              {run.cuda_peak_allocated_bytes == null
                                ? '未提供'
                                : (run.cuda_peak_allocated_bytes / 1024 ** 2).toFixed(2)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="research-run-details">
                    {research.data.runs.map((run) => (
                      <details key={`${run.variant}-${run.seed}`}>
                        <summary>
                          {run.variant}{' '}
                          <span className="mono">
                            seed {run.seed} · {run.device} / {run.precision}
                          </span>
                        </summary>
                        <dl className="run-identity">
                          <div>
                            <dt>最佳权重 SHA256</dt>
                            <dd>{run.best_sha256 ?? '未提供'}</dd>
                          </div>
                          <div>
                            <dt>Git SHA</dt>
                            <dd>{run.git_sha ?? '未提供'}</dd>
                          </div>
                          <div>
                            <dt>峰值 CPU 内存 / bytes</dt>
                            <dd>{run.cpu_peak_memory_bytes ?? '未提供'}</dd>
                          </div>
                        </dl>
                        <h3>训练配置</h3>
                        <Configuration values={run.config} />
                        <h3>模型配置</h3>
                        <Configuration values={run.model_config} />
                        <h3>运行环境</h3>
                        <Configuration values={run.versions} />
                      </details>
                    ))}
                  </div>
                </>
              ) : (
                <p className="research-pending">公开报告未提供训练运行明细。</p>
              )}
            </section>
            <section className="research-failure-section" aria-label="真实失败案例">
              <h2>失败案例，而非精选展示</h2>
              <p className="panel-note">
                每幅图来自公开报告的固定选择规则，展示 PREDICTION 与 DERIVED ANNOTATION
                的差异。低分、空边界与失败形态均保留；图像不是新运行的实验。
              </p>
              {research.data.failure_cases?.length ? (
                <div className="research-failures">
                  {research.data.failure_cases.map((failure) => (
                    <figure key={failure.variant} className="research-failure">
                      <figcaption>
                        <h3>{failure.variant}</h3>
                        <p>{failure.selection}</p>
                        <div className="failure-metadata mono">
                          <span>
                            {failure.metrics.sequence_id ?? '序列未知'} / F
                            {failure.metrics.source_target_index ?? '—'} / Lead{' '}
                            {failure.metrics.lead ?? '—'}
                          </span>
                          <span>seed {failure.metrics.seed ?? '不适用'}</span>
                          <span>
                            IoU {formatMetric(failure.metrics.iou)} / Dice{' '}
                            {formatMetric(failure.metrics.dice)}
                          </span>
                        </div>
                      </figcaption>
                      <ResearchFigure url={failure.png_url} variant={failure.variant} />
                      <details>
                        <summary>图像校验与选中样本指标</summary>
                        <dl>
                          <div>
                            <dt>PNG SHA256</dt>
                            <dd>{failure.png_sha256}</dd>
                          </div>
                          {Object.entries(metricLabels).map(([key, label]) => (
                            <div key={key}>
                              <dt>{label}</dt>
                              <dd>{formatMetric(failure.metrics[key as MetricKey])}</dd>
                            </div>
                          ))}
                        </dl>
                      </details>
                    </figure>
                  ))}
                </div>
              ) : (
                <p className="research-pending">公开报告未提供失败案例图。</p>
              )}
            </section>
            <section className="research-provenance">
              <h2>报告溯源</h2>
              {reports.map((report) => (
                <details key={report.id}>
                  <summary>
                    {report.label}{' '}
                    <span className="mono">
                      {report.provenance.split.toUpperCase()} / {report.provenance.target}
                    </span>
                  </summary>
                  <dl>
                    <div>
                      <dt>报告 / 模型</dt>
                      <dd>
                        {report.id} / {report.model_id}
                      </dd>
                    </div>
                    <div>
                      <dt>Seeds</dt>
                      <dd>
                        {report.seeds.length ? report.seeds.join(', ') : '经典基线，无训练 seed'}
                      </dd>
                    </div>
                    <div>
                      <dt>Git SHA</dt>
                      <dd>{report.provenance.git_sha ?? '未提供'}</dd>
                    </div>
                    <div>
                      <dt>Manifest SHA256</dt>
                      <dd>{report.provenance.manifest_sha256 ?? '未提供'}</dd>
                    </div>
                  </dl>
                </details>
              ))}
            </section>
          </>
        )}
      </QueryState>
    </main>
  );
}

function formatMetric(value: number | boolean | null | undefined) {
  return typeof value === 'boolean' ? (value ? '是' : '否') : format(value);
}

function displayValue(value: unknown): string {
  if (value == null) return '未提供';
  if (Array.isArray(value)) return value.map(displayValue).join(', ');
  return String(value);
}

function Configuration({ values }: { values: Record<string, unknown> }) {
  return (
    <dl className="research-configuration">
      {Object.entries(values).map(([key, value]) => (
        <div key={key}>
          <dt>{key}</dt>
          <dd>
            {value !== null && typeof value === 'object' && !Array.isArray(value) ? (
              <Configuration values={value as Record<string, unknown>} />
            ) : (
              displayValue(value)
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function ResearchFigure({ url, variant }: { url: string; variant: string }) {
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  return failed ? (
    <div className="failure-image-error" role="alert">
      {variant} 失败案例图未能读取。
      <button
        onClick={() => {
          setFailed(false);
          setAttempt(attempt + 1);
        }}
      >
        重试案例图
      </button>
    </div>
  ) : (
    <a
      href={url}
      target="_blank"
      rel="noreferrer noopener"
      aria-label={`打开 ${variant} 完整失败案例图`}
    >
      <img
        src={attempt ? `${url}${url.includes('?') ? '&' : '?'}retry=${attempt}` : url}
        alt={`${variant} 真实失败案例：预测与派生目标对比`}
        loading="lazy"
        onError={() => setFailed(true)}
      />
    </a>
  );
}

function ResearchChart({ reports, metric }: { reports: ResearchReport[]; metric: MetricKey }) {
  const values = reports.flatMap((report) =>
    report.metrics.flatMap((point) => {
      const value = point.mean[metric];
      const sd = point.sample_sd?.[metric] ?? 0;
      return value == null || !Number.isFinite(value) ? [] : [value - sd, value + sd];
    }),
  );
  if (!values.length) return <p className="research-pending">所选指标没有可评估数值。</p>;
  const low = Math.min(...values);
  const high = Math.max(...values);
  const margin = Math.max((high - low) * 0.12, Math.abs(high) * 0.03, 0.001);
  const yLow = low - margin;
  const yHigh = high + margin;
  const leads = [
    ...new Set(reports.flatMap((report) => report.metrics.map((point) => point.lead))),
  ].sort((a, b) => a - b);
  const x = (lead: number) =>
    80 + ((lead - leads[0]) / Math.max(1, leads[leads.length - 1] - leads[0])) * 850;
  const y = (value: number) => 290 - ((value - yLow) / (yHigh - yLow)) * 250;
  return (
    <svg
      className="research-chart"
      role="img"
      aria-label={`${metricLabels[metric]}随 lead 变化，数值见下方报告表`}
      viewBox="0 0 1000 340"
    >
      <title>{metricLabels[metric]} · 报告离散 lead 与 sample SD</title>
      {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
        const value = yLow + (yHigh - yLow) * ratio;
        return (
          <g key={ratio}>
            <line x1="80" x2="950" y1={y(value)} y2={y(value)} stroke="#2a3941" />
            <text x="65" y={y(value) + 4} textAnchor="end">
              {value.toFixed(3)}
            </text>
          </g>
        );
      })}
      {leads.map((lead) => (
        <text key={lead} x={x(lead)} y="315" textAnchor="middle">
          {lead}
        </text>
      ))}
      <text x="950" y="335" textAnchor="end">
        LEAD / frame
      </text>
      {reports.map((report, index) => {
        const color = seriesColors[index % seriesColors.length];
        const sorted = [...report.metrics].sort((a, b) => a.lead - b.lead);
        return (
          <g key={report.id} data-model-id={report.model_id}>
            {sorted.map((point, i) => {
              const value = point.mean[metric];
              const previous = sorted[i - 1];
              const before = previous?.mean[metric];
              if (value == null || !Number.isFinite(value)) return null;
              const sd = point.sample_sd?.[metric];
              return (
                <g key={point.lead}>
                  {before != null && Number.isFinite(before) && (
                    <line
                      x1={x(previous.lead)}
                      y1={y(before)}
                      x2={x(point.lead)}
                      y2={y(value)}
                      stroke={color}
                      strokeWidth="1.7"
                      strokeDasharray={index > 1 ? '5 3' : undefined}
                    />
                  )}
                  {sd != null && Number.isFinite(sd) && (
                    <g stroke={color} opacity=".7">
                      <line
                        x1={x(point.lead)}
                        x2={x(point.lead)}
                        y1={y(value - sd)}
                        y2={y(value + sd)}
                      />
                      <line
                        x1={x(point.lead) - 4}
                        x2={x(point.lead) + 4}
                        y1={y(value - sd)}
                        y2={y(value - sd)}
                      />
                      <line
                        x1={x(point.lead) - 4}
                        x2={x(point.lead) + 4}
                        y1={y(value + sd)}
                        y2={y(value + sd)}
                      />
                    </g>
                  )}
                  <circle cx={x(point.lead)} cy={y(value)} r="3.5" fill={color}>
                    <title>
                      {report.label} · Lead {point.lead}: {format(value)}, sample SD {format(sd)},
                      n={point.n}
                    </title>
                  </circle>
                </g>
              );
            })}
          </g>
        );
      })}
    </svg>
  );
}
