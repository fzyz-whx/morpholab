import { useCallback, useEffect, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { frameUrl, splitLabel, useDatasets, useSequence, useSequences } from './api';
import type { Layer, SequenceDetail } from './api';
import { Arrow, ModelState, QueryState, SourceDetails } from './components';
import PredictionPanel, { PredictionMetrics } from './PredictionPanel';
import type { PredictionResult } from './prediction-api';

const layerNames: Record<Layer, string> = {
  observed: '真实观测',
  annotation: '原始注释',
  overlay: '轮廓叠加',
};

export default function Studio() {
  const { sequenceId = '' } = useParams();
  const sequence = useSequence(sequenceId);
  return (
    <main id="main" className="studio-page">
      <p className="desktop-workbench-note">
        完整形态实验建议使用至少1280px宽的桌面窗口。移动端可阅读来源、序列元信息与研究记录。
      </p>
      <QueryState
        pending={sequence.isPending}
        error={sequence.error}
        retry={() => {
          void sequence.refetch();
        }}
      >
        {sequence.data && <StudioWorkspace key={sequenceId} sequence={sequence.data} />}
      </QueryState>
    </main>
  );
}

function StudioWorkspace({ sequence }: { sequence: SequenceDetail }) {
  const [frame, setFrame] = useState(0);
  const [layer, setLayer] = useState<Layer>('overlay');
  const [manualZoom, setManualZoom] = useState<number | null>(null);
  const [viewportSize, setViewportSize] = useState({ width: 128, height: 128 });
  const viewportRef = useRef<HTMLDivElement>(null);
  const [playing, setPlaying] = useState(false);
  const [inspectorTab, setInspectorTab] = useState<'frame' | 'prediction'>('frame');
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [showPrediction, setShowPrediction] = useState(true);
  const [showError, setShowError] = useState(false);
  const [showPrevious, setShowPrevious] = useState(false);
  const [coordinates, setCoordinates] = useState<{ x: number; y: number; key: string } | null>(
    null,
  );
  const coordinateKey = `${frame}-${layer}-${manualZoom}-${viewportSize.width}-${viewportSize.height}`;
  const activeCoordinates = coordinates?.key === coordinateKey ? coordinates : null;
  const predictedFrame = prediction?.frames.find((item) => item.source_frame_index === frame);
  const receivePrediction = useCallback((result: PredictionResult) => {
    setPrediction(result);
    setPlaying(false);
    if (result.frames[0]) setFrame(result.frames[0].source_frame_index);
    setShowPrediction(true);
  }, []);
  const datasets = useDatasets();
  const sequences = useSequences(sequence.dataset_id);
  const dataset = datasets.data?.find((d) => d.id === sequence.dataset_id);
  const last = Math.max(0, sequence.frame_count - 1);
  const metadata = sequence.frames.find((f) => f.frame_index === frame);
  const fitZoom = Math.max(
    0.01,
    Math.floor(
      Math.min(viewportSize.width / sequence.width, viewportSize.height / sequence.height) * 100,
    ) / 100,
  );
  const zoom = manualZoom ?? fitZoom;

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    function measure() {
      if (!viewport) return;
      const style = getComputedStyle(viewport);
      const width =
        viewport.clientWidth -
        parseFloat(style.paddingLeft || '0') -
        parseFloat(style.paddingRight || '0');
      const height =
        viewport.clientHeight -
        parseFloat(style.paddingTop || '0') -
        parseFloat(style.paddingBottom || '0');
      if (width > 0 && height > 0) setViewportSize({ width, height });
    }
    measure();
    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', measure);
      return () => window.removeEventListener('resize', measure);
    }
    const observer = new ResizeObserver(([entry]) => {
      if (entry && entry.contentRect.width > 0 && entry.contentRect.height > 0)
        setViewportSize({ width: entry.contentRect.width, height: entry.contentRect.height });
    });
    observer.observe(viewport);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (manualZoom === null && viewportRef.current) {
      viewportRef.current.scrollTop = 0;
      viewportRef.current.scrollLeft = 0;
    }
  }, [manualZoom, viewportSize]);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      if (frame >= last) setPlaying(false);
      else setFrame(frame + 1);
    }, 300);
    return () => window.clearInterval(timer);
  }, [playing, frame, last]);

  function seek(next: number) {
    setPlaying(false);
    setFrame(Math.max(0, Math.min(last, next)));
  }
  function togglePlay() {
    if (playing) setPlaying(false);
    else {
      if (frame >= last) setFrame(0);
      setPlaying(true);
    }
  }
  function keyboard(event: KeyboardEvent<HTMLElement>) {
    if (
      event.target instanceof HTMLInputElement ||
      event.target instanceof HTMLSelectElement ||
      event.target instanceof HTMLButtonElement ||
      event.target instanceof HTMLAnchorElement
    )
      return;
    if (['ArrowLeft', 'ArrowRight', 'Home', 'End', ' '].includes(event.key)) event.preventDefault();
    if (event.key === 'ArrowLeft') seek(frame - 1);
    if (event.key === 'ArrowRight') seek(frame + 1);
    if (event.key === 'Home') seek(0);
    if (event.key === 'End') seek(last);
    if (event.key === ' ') togglePlay();
  }

  return (
    <>
      <div className="studio-heading">
        <div className="breadcrumbs">
          <Link to="/datasets">数据档案</Link>
          <span>/</span>
          <span>DROSOPHILA</span>
          <span>/</span>
          <strong>{sequence.id}</strong>
        </div>
        <div className="studio-heading-meta">
          <span className="status-dot" />
          真实观测
          <span className="muted">{prediction ? 'PREDICTION · 形态推理' : '观测与原注释'}</span>
        </div>
      </div>
      <div className="studio-layout">
        <aside className="studio-sidebar">
          <div className="sidebar-section">
            <span className="eyebrow">EXPERIMENT</span>
            <h1>{sequence.id}</h1>
            <p>
              果蝇胚胎
              <br />
              in vivo 激光创面闭合
            </p>
            <div className="mini-facts">
              <span>{sequence.frame_count} frames</span>
              <span>
                {sequence.width} × {sequence.height} px
              </span>
            </div>
            {prediction && (
              <>
                <button
                  className="prediction-layer-toggle"
                  aria-pressed={showPrediction}
                  onClick={() => setShowPrediction(!showPrediction)}
                >
                  <span className="prediction-line" />
                  预测轮廓 <span className="mono">PREDICTION</span>
                </button>
                <button
                  className="prediction-layer-toggle"
                  aria-pressed={showError}
                  onClick={() => setShowError(!showError)}
                >
                  派生区域误差 <span className="mono">FP / FN</span>
                </button>
              </>
            )}
          </div>
          <div className="sidebar-section">
            <span className="eyebrow">VIEW LAYERS</span>
            <div className="layer-controls">
              {(Object.keys(layerNames) as Layer[]).map((item) => (
                <button key={item} onClick={() => setLayer(item)} aria-pressed={layer === item}>
                  <span className={`layer-symbol ${item}`} />
                  {layerNames[item]}
                  <span className="layer-key">
                    {item === 'observed' ? 'OBS' : item === 'annotation' ? 'ANN' : 'OBS + ANN'}
                  </span>
                </button>
              ))}
            </div>
            <button
              className="previous-frame-toggle"
              disabled={frame === 0}
              aria-pressed={showPrevious && frame > 0}
              onClick={() => setShowPrevious(!showPrevious)}
            >
              前帧参照
            </button>
            {showPrevious && frame > 0 && (
              <PreviousFrame
                key={`${sequence.id}-${frame - 1}`}
                sequenceId={sequence.id}
                frame={frame - 1}
              />
            )}
          </div>
          <div className="sidebar-section sequence-section">
            <div className="section-topline">
              <span className="eyebrow">SEQUENCES</span>
              <span className="mono muted">{sequences.data?.length ?? '—'}</span>
            </div>
            <QueryState
              pending={sequences.isPending}
              error={sequences.error}
              retry={() => {
                void sequences.refetch();
              }}
            >
              <nav className="sequence-nav" aria-label="实验序列">
                {sequences.data?.map((s) => (
                  <Link
                    key={s.id}
                    to={`/studio/${s.id}`}
                    aria-current={s.id === sequence.id ? 'page' : undefined}
                  >
                    <span className="mono">{s.id}</span>
                    <span>{splitLabel(s.project_split)}</span>
                  </Link>
                ))}
              </nav>
            </QueryState>
          </div>
        </aside>
        <section className="science-column" onKeyDown={keyboard} aria-label="科学画布与时间轴">
          <div className="canvas-toolbar">
            <div className="canvas-layer-label">
              <span className="status-dot" />
              {layer === 'annotation'
                ? 'ANNOTATION'
                : layer === 'overlay'
                  ? 'OBSERVED + ANNOTATION'
                  : 'OBSERVED'}
            </div>
            <button className="prediction-open" onClick={() => setInspectorTab('prediction')}>
              预测实验
            </button>
            <label className="zoom-control">
              <span>缩放</span>
              <input
                aria-label="画布缩放"
                type="range"
                min={Math.min(0.25, fitZoom)}
                max={Math.max(8, fitZoom)}
                step="0.01"
                value={zoom}
                onChange={(e) => setManualZoom(Number(e.target.value))}
              />
              <output className="mono">{Math.round(zoom * 100)}%</output>
            </label>
            <button
              className="fit-button"
              aria-label="适合画布"
              aria-pressed={manualZoom === null}
              onClick={() => setManualZoom(null)}
            >
              适合画布{manualZoom === null && ' · FIT'}
            </button>
          </div>
          <div
            className="scientific-viewport"
            ref={viewportRef}
            data-view-mode={manualZoom === null ? 'fit' : 'manual'}
            tabIndex={0}
            aria-label="影像画布，方向键逐帧，空格播放，Home和End跳转首尾"
          >
            <output className="viewport-coordinate coord-top" aria-label="原始图像坐标">
              X {activeCoordinates ? String(activeCoordinates.x).padStart(3, '0') : '—'} / Y{' '}
              {activeCoordinates ? String(activeCoordinates.y).padStart(3, '0') : '—'}
            </output>
            <FrameImage
              key={`${sequence.id}-${frame}-${layer}`}
              src={frameUrl(sequence.id, frame, layer)}
              alt={`${sequence.id} 第 ${frame} 帧 · ${layerNames[layer]}`}
              width={sequence.width * zoom}
              height={sequence.height * zoom}
              prediction={showPrediction ? predictedFrame : undefined}
              predictionGrid={prediction?.grid}
              showError={showError}
              sourceWidth={sequence.width}
              sourceHeight={sequence.height}
              onCoordinates={(point) =>
                setCoordinates(point ? { ...point, key: coordinateKey } : null)
              }
            />
            <span className="viewport-coordinate coord-bottom">
              {sequence.width} × {sequence.height} PIXEL GRID
            </span>
            <span className="viewport-frame mono">F {String(frame).padStart(3, '0')}</span>
          </div>
          <div className="canvas-legend">
            <span>
              <i className="legend-observed" />
              OBSERVED · 实测影像
            </span>
            {layer !== 'observed' && (
              <span>
                <i className="legend-annotation" />
                ANNOTATION · 原始薄轮廓
              </span>
            )}
            {prediction && showPrediction && predictedFrame && (
              <span className="prediction-ink">
                <i className="legend-prediction" />
                PREDICTION · Lead {predictedFrame.lead} · 虚线轮廓
              </span>
            )}
            {prediction && showPrediction && showError && predictedFrame?.target_valid && (
              <span>误差层：琥珀 FP 多预测 / 玫红 FN 漏预测 · DERIVED TARGET</span>
            )}
            <span className="muted">
              {prediction ? '灰度原帧为 OBSERVED · 非生成影像' : '显示转换 · 非预测'}
            </span>
          </div>
          <Timeline
            frame={frame}
            last={last}
            playing={playing}
            onSeek={seek}
            onToggle={togglePlay}
            invalidFrames={sequence.frames.filter((f) => !f.qc_valid).map((f) => f.frame_index)}
            predictionRequest={prediction?.request}
          />
          <div className="canvas-bottom-note">
            <span>
              ← → 逐帧 <span className="divider-text">/</span> Space 播放
            </span>
            <span>时间单位未核实 · 按 frame 浏览</span>
          </div>
        </section>
        <aside className="inspector">
          <div className="inspector-tabs" role="group" aria-label="工作台检查面板">
            <button
              aria-pressed={inspectorTab === 'frame'}
              onClick={() => setInspectorTab('frame')}
            >
              帧检查
            </button>
            <button
              aria-pressed={inspectorTab === 'prediction'}
              onClick={() => setInspectorTab('prediction')}
            >
              预测实验
            </button>
          </div>
          <div hidden={inspectorTab !== 'prediction'}>
            <PredictionPanel
              sequence={sequence}
              frame={frame}
              onResult={receivePrediction}
              onClear={() => setPrediction(null)}
            />
            {prediction && <PredictionMetrics result={prediction} current={predictedFrame} />}
          </div>
          <div hidden={inspectorTab !== 'frame'}>
            <section className="inspector-section">
              <span className="eyebrow">FRAME INSPECTOR</span>
              <div className="frame-title">
                <span>当前帧</span>
                <strong className="mono">
                  {String(frame).padStart(3, '0')}
                  <small> / {last}</small>
                </strong>
              </div>
              <div className={`qc-state ${metadata?.qc_valid ? 'valid' : 'invalid'}`}>
                <span className={metadata?.qc_valid ? 'status-dot' : 'hollow-dot'} />
                {metadata?.qc_valid ? '轮廓 QC 通过' : '轮廓 QC 未通过'}
              </div>
              <dl className="inspector-facts">
                <div>
                  <dt>原注释</dt>
                  <dd>骨架化薄轮廓</dd>
                </div>
                <div>
                  <dt>触及图边</dt>
                  <dd>
                    {metadata ? (metadata.touches_border ? '是 · 不用于训练窗口' : '否') : '未知'}
                  </dd>
                </div>
                <div>
                  <dt>有效 QC</dt>
                  <dd className="mono">
                    {sequence.qc_valid_count} / {sequence.frame_count}
                  </dd>
                </div>
                <div>
                  <dt>QC 范围</dt>
                  <dd>
                    {sequence.qc_definition?.includes('source-only')
                      ? '仅原轮廓检查'
                      : '轮廓与派生目标'}
                  </dd>
                </div>
                <div>
                  <dt>本项目划分</dt>
                  <dd>{splitLabel(sequence.project_split)}</dd>
                </div>
                <div>
                  <dt>官方划分</dt>
                  <dd>{sequence.official_split ?? '未知'}</dd>
                </div>
                <div>
                  <dt>帧时间</dt>
                  <dd>
                    {metadata?.timestamp_min != null ? `${metadata.timestamp_min} min` : '未核实'}
                  </dd>
                </div>
              </dl>
              {!metadata?.qc_valid && (
                <p className="qc-explanation">
                  此帧仍保留可见。包含该帧的训练或评估窗口将排除，不自动补线。
                </p>
              )}
            </section>
            <section className="inspector-section">
              <ModelState />
            </section>
            <section className="inspector-section">
              <SourceDetails compact dataset={dataset} />
            </section>
            <div className="inspector-bottom">
              <Link to="/methods">
                标签与划分协议 <Arrow />
              </Link>
            </div>
          </div>
        </aside>
      </div>
      <footer className="studio-statusbar">
        <span>
          <span className="status-dot" />
          LOCAL DATA / READ ONLY
        </span>
        <span>morpholab-split-v1</span>
        <span>{dataset?.license ?? '许可读取中'}</span>
        <span>
          {prediction
            ? `${prediction.device.toUpperCase()} / ${prediction.request.model_id} / MODEL ${prediction.model.model_git_sha?.slice(0, 7) ?? 'CLASSICAL'}`
            : '原始数据浏览 / 预测按需运行'}
        </span>
      </footer>
    </>
  );
}

function FrameImage({
  src,
  alt,
  width,
  height,
  prediction,
  predictionGrid,
  showError,
  sourceWidth,
  sourceHeight,
  onCoordinates,
}: {
  src: string;
  alt: string;
  width: number;
  height: number;
  prediction?: import('./prediction-api').PredictedFrame;
  predictionGrid?: { width: number; height: number };
  showError?: boolean;
  sourceWidth: number;
  sourceHeight: number;
  onCoordinates: (point: { x: number; y: number } | null) => void;
}) {
  const [state, setState] = useState<'loading' | 'loaded' | 'error'>('loading');
  const [attempt, setAttempt] = useState(0);
  return (
    <>
      <div
        className="frame-geometry"
        style={{ width, height, position: 'relative', flexShrink: 0 }}
        onMouseMove={(event) => {
          const rect = event.currentTarget.getBoundingClientRect();
          const x = event.clientX - rect.left;
          const y = event.clientY - rect.top;
          onCoordinates(
            state === 'loaded' &&
              rect.width > 0 &&
              rect.height > 0 &&
              x >= 0 &&
              y >= 0 &&
              x < rect.width &&
              y < rect.height
              ? {
                  x: Math.floor((x / rect.width) * sourceWidth),
                  y: Math.floor((y / rect.height) * sourceHeight),
                }
              : null,
          );
        }}
        onMouseLeave={() => onCoordinates(null)}
      >
        <img
          className="scientific-image"
          src={attempt ? `${src}&retry=${attempt}` : src}
          alt={alt}
          width={width}
          height={height}
          onLoad={() => setState('loaded')}
          onError={() => {
            setState('error');
            onCoordinates(null);
          }}
          style={{ width, height, visibility: state === 'loaded' ? 'visible' : 'hidden' }}
        />
        {prediction &&
          showError &&
          prediction.target_valid &&
          prediction.images.error &&
          state === 'loaded' && (
            <ErrorImage key={prediction.images.error.url} url={prediction.images.error.url} />
          )}
        {prediction && predictionGrid && state === 'loaded' && (
          <svg
            className="prediction-overlay"
            role="img"
            aria-label={`PREDICTION Lead ${prediction.lead}，工作网格预测轮廓`}
            viewBox={`-0.5 -0.5 ${predictionGrid.width} ${predictionGrid.height}`}
            preserveAspectRatio="none"
          >
            <title>PREDICTION · 预测轮廓，非原始注释</title>
            {prediction.contours.map((points, index) => (
              <polyline
                key={index}
                points={points.map(([x, y]) => `${x},${y}`).join(' ')}
                fill="none"
                stroke="#E2B875"
                strokeWidth="1.5"
                strokeDasharray="5 3"
                vectorEffect="non-scaling-stroke"
              />
            ))}
          </svg>
        )}
      </div>
      {state === 'loading' && (
        <div className="image-feedback" role="status">
          正在读取真实帧…
        </div>
      )}
      {state === 'error' && (
        <div className="image-feedback" role="alert">
          <p>影像读取失败</p>
          <button
            onClick={() => {
              setState('loading');
              setAttempt(attempt + 1);
            }}
          >
            重新读取此帧
          </button>
        </div>
      )}
    </>
  );
}

function ErrorImage({ url }: { url: string }) {
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  return (
    <>
      {!failed && (
        <img
          className="prediction-error-image"
          src={attempt ? `${url}${url.includes('?') ? '&' : '?'}retry=${attempt}` : url}
          alt="派生区域误差层：FP 多预测 / FN 漏预测"
          onError={() => setFailed(true)}
        />
      )}
      {failed && (
        <div className="overlay-asset-error" role="alert">
          误差图加载失败
          <button
            onClick={() => {
              setFailed(false);
              setAttempt(attempt + 1);
            }}
          >
            重试误差图
          </button>
        </div>
      )}
    </>
  );
}

function PreviousFrame({ sequenceId, frame }: { sequenceId: string; frame: number }) {
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const url = frameUrl(sequenceId, frame, 'observed');
  return (
    <figure className="previous-frame-reference">
      <figcaption>
        <span>OBSERVED / 前帧参照</span>
        <strong className="mono">F{String(frame).padStart(3, '0')}</strong>
      </figcaption>
      {!failed ? (
        <img
          src={attempt ? `${url}&retry=${attempt}` : url}
          alt={`${sequenceId} 前一真实观测帧 ${frame}`}
          onError={() => setFailed(true)}
        />
      ) : (
        <div role="alert">
          前帧读取失败
          <button
            onClick={() => {
              setFailed(false);
              setAttempt(attempt + 1);
            }}
          >
            重试前帧
          </button>
        </div>
      )}
    </figure>
  );
}

export function Timeline({
  frame,
  last,
  playing,
  onSeek,
  onToggle,
  invalidFrames,
  predictionRequest,
}: {
  frame: number;
  last: number;
  playing: boolean;
  onSeek: (n: number) => void;
  onToggle: () => void;
  invalidFrames: number[];
  predictionRequest?: import('./prediction-api').PredictionRequest;
}) {
  return (
    <section className="timeline" aria-label="帧时间轴">
      <div className="timeline-heading">
        <span className="eyebrow">OBSERVATION TIMELINE</span>
        <span className="mono">
          FRAME <strong>{String(frame).padStart(3, '0')}</strong>{' '}
          <span className="muted">/ {last}</span>
        </span>
      </div>
      {predictionRequest && (
        <div className="timeline-window-labels" aria-label="实验时间范围">
          <span>
            HISTORY F{predictionRequest.observation_start}–
            {predictionRequest.observation_start + predictionRequest.observations - 1}
          </span>
          <span className="prediction-ink">
            PREDICTION F{predictionRequest.observation_start + predictionRequest.observations}–
            {predictionRequest.observation_start +
              predictionRequest.observations +
              predictionRequest.horizon -
              1}
          </span>
        </div>
      )}
      <div className="timeline-track">
        {predictionRequest && (
          <div className="timeline-ranges" aria-hidden="true">
            <span
              className="history-range"
              style={{
                left: `${(predictionRequest.observation_start / Math.max(1, last)) * 100}%`,
                width: `${((predictionRequest.observations - 1) / Math.max(1, last)) * 100}%`,
              }}
            />
            <span
              className="prediction-range"
              style={{
                left: `${((predictionRequest.observation_start + predictionRequest.observations) / Math.max(1, last)) * 100}%`,
                width: `${((predictionRequest.horizon - 1) / Math.max(1, last)) * 100}%`,
              }}
            />
          </div>
        )}
        <div className="qc-track" aria-hidden="true">
          {invalidFrames.map((i) => (
            <i key={i} style={{ left: `${last ? (i / last) * 100 : 0}%` }} />
          ))}
        </div>
        <input
          type="range"
          aria-label="选择帧"
          aria-valuetext={`第 ${frame} 帧，共 ${last + 1} 帧`}
          min={0}
          max={last}
          step={1}
          value={frame}
          onChange={(e) => onSeek(Number(e.target.value))}
        />
        <div className="timeline-ticks" aria-hidden="true">
          {[0, 0.25, 0.5, 0.75, 1].map((n) => (
            <span key={n}>{Math.round(n * last)}</span>
          ))}
        </div>
      </div>
      <div className="playback-row">
        <div className="playback-buttons">
          <button aria-label="首帧" disabled={frame === 0} onClick={() => onSeek(0)}>
            │‹
          </button>
          <button aria-label="上一帧" disabled={frame === 0} onClick={() => onSeek(frame - 1)}>
            <Arrow direction="left" />
          </button>
          <button
            className="play-button"
            aria-label={playing ? '暂停' : '播放'}
            onClick={onToggle}
            disabled={last === 0}
          >
            {playing ? (
              <>
                <span aria-hidden="true">Ⅱ</span>暂停
              </>
            ) : (
              <>
                <span aria-hidden="true">▷</span>播放
              </>
            )}
          </button>
          <button aria-label="下一帧" disabled={frame === last} onClick={() => onSeek(frame + 1)}>
            <Arrow />
          </button>
          <button aria-label="末帧" disabled={frame === last} onClick={() => onSeek(last)}>
            ›│
          </button>
        </div>
        <span className="timeline-qc-key">
          <i />
          QC 未通过 · {invalidFrames.length} frames
        </span>
      </div>
    </section>
  );
}
