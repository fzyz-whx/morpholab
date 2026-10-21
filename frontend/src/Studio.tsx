import { useEffect, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { frameUrl, splitLabel, useDatasets, useSequence, useSequences } from './api';
import type { Layer, SequenceDetail } from './api';
import { Arrow, ModelState, QueryState, SourceDetails } from './components';

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
          真实观测<span className="muted">模型未训练</span>
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
            <span className="viewport-coordinate coord-top">X 000 / Y 000</span>
            <FrameImage
              key={`${sequence.id}-${frame}-${layer}`}
              src={frameUrl(sequence.id, frame, layer)}
              alt={`${sequence.id} 第 ${frame} 帧 · ${layerNames[layer]}`}
              width={sequence.width * zoom}
              height={sequence.height * zoom}
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
            <span className="muted">显示转换 · 非预测</span>
          </div>
          <Timeline
            frame={frame}
            last={last}
            playing={playing}
            onSeek={seek}
            onToggle={togglePlay}
            invalidFrames={sequence.frames.filter((f) => !f.qc_valid).map((f) => f.frame_index)}
          />
          <div className="canvas-bottom-note">
            <span>
              ← → 逐帧 <span className="divider-text">/</span> Space 播放
            </span>
            <span>时间单位未核实 · 按 frame 浏览</span>
          </div>
        </section>
        <aside className="inspector">
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
        </aside>
      </div>
      <footer className="studio-statusbar">
        <span>
          <span className="status-dot" />
          LOCAL DATA / READ ONLY
        </span>
        <span>morpholab-split-v1</span>
        <span>{dataset?.license ?? '许可读取中'}</span>
        <span>未训练 · 未评估</span>
      </footer>
    </>
  );
}

function FrameImage({
  src,
  alt,
  width,
  height,
}: {
  src: string;
  alt: string;
  width: number;
  height: number;
}) {
  const [state, setState] = useState<'loading' | 'loaded' | 'error'>('loading');
  const [attempt, setAttempt] = useState(0);
  return (
    <>
      <img
        className="scientific-image"
        src={attempt ? `${src}&retry=${attempt}` : src}
        alt={alt}
        width={width}
        height={height}
        onLoad={() => setState('loaded')}
        onError={() => setState('error')}
        style={{ width, height, visibility: state === 'loaded' ? 'visible' : 'hidden' }}
      />
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

export function Timeline({
  frame,
  last,
  playing,
  onSeek,
  onToggle,
  invalidFrames,
}: {
  frame: number;
  last: number;
  playing: boolean;
  onSeek: (n: number) => void;
  onToggle: () => void;
  invalidFrames: number[];
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
      <div className="timeline-track">
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
