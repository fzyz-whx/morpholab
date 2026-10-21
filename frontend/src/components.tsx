import type { ReactNode } from 'react';
import type { Dataset } from './api';
import { useModels } from './prediction-api';

export function Arrow({ direction = 'right' }: { direction?: 'right' | 'left' }) {
  return (
    <svg
      aria-hidden="true"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      style={{ transform: direction === 'left' ? 'rotate(180deg)' : undefined }}
    >
      <path d="M4 12h15m-6-6 6 6-6 6" />
    </svg>
  );
}
export function QueryState({
  pending,
  error,
  empty,
  retry,
  children,
}: {
  pending: boolean;
  error: Error | null;
  empty?: boolean;
  retry: () => void;
  children: ReactNode;
}) {
  if (pending)
    return (
      <div className="query-state" role="status">
        <span className="status-dot" />
        正在读取实验记录…
      </div>
    );
  if (error)
    return (
      <div className="query-state error" role="alert">
        <span className="eyebrow">DATA SERVICE</span>
        <h2>无法读取数据</h2>
        <p>{error.message}</p>
        <button onClick={retry}>
          重新读取 <Arrow />
        </button>
      </div>
    );
  if (empty)
    return (
      <div className="query-state">
        <span className="eyebrow">NO RECORDS</span>
        <h2>当前没有可用记录</h2>
        <p>导入并审计本地数据后，实验记录会显示在这里。</p>
      </div>
    );
  return children;
}
export function SourceDetails({
  dataset,
  compact = false,
}: {
  dataset?: Dataset;
  compact?: boolean;
}) {
  if (!dataset) return <p className="muted">来源元数据尚未读取。</p>;
  return (
    <div className={compact ? 'source-details compact' : 'source-details'}>
      <div className="eyebrow">SOURCE PROVENANCE</div>
      <p>{dataset.name}</p>
      <dl>
        <div>
          <dt>来源</dt>
          <dd>
            <a href={dataset.source_url} target="_blank" rel="noreferrer">
              {dataset.doi ? `DOI ${dataset.doi}` : '官方记录'} ↗
            </a>
          </dd>
        </div>
        <div>
          <dt>许可</dt>
          <dd>{dataset.license ?? '未核实'}</dd>
        </div>
      </dl>
      <p className="source-caption">
        Backová 等，2023 · 显示图像经本地可视化转换，原始文件保留于本地。
      </p>
    </div>
  );
}
export function ModelState() {
  const models = useModels();
  const available = models.data?.filter((model) => model.available) ?? [];
  const trained = available.filter((model) => model.trained);
  return (
    <div className="model-state">
      <span className="eyebrow">MODEL STATUS</span>
      <div className="model-title">
        <span className="hollow-dot" />
        {models.isPending
          ? '正在读取模型'
          : models.error
            ? '模型状态未取得'
            : `${available.length} 个可用模型`}
      </div>
      <p>
        {models.isPending
          ? '从本地模型注册表读取，不据页面推断训练状态。'
          : models.error
            ? '模型服务暂不可用，请在预测实验面板重试。'
            : trained.length
              ? `${trained.length} 个已训练模型；仅加载既有权重进行形态推理。研究结论以公开评估报告为准。`
              : '当前无可用的已训练模型。经典基线无需训练；可用性由本地注册表确定。'}
      </p>
    </div>
  );
}
