import { Link, NavLink, Route, Routes } from 'react-router-dom';
import { useState } from 'react';
import { PRIMARY_DATASET, frameUrl, splitLabel, useDatasets, useSequences } from './api';
import { Arrow, ModelState, QueryState, SourceDetails } from './components';
import Studio from './Studio';
import Research from './Research';

function Shell() {
  return (
    <>
      <a className="skip-link" href="#main">
        跳到正文
      </a>
      <header className="app-header">
        <Link to="/" className="brand" aria-label="MorphoLab 首页">
          <span className="brand-glyph" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
          MorphoLab<span className="brand-sub">形态实验室</span>
        </Link>
        <nav aria-label="主导航">
          <NavLink to="/" end>
            Overview <span>概览</span>
          </NavLink>
          <NavLink to="/datasets">
            Archive <span>数据档案</span>
          </NavLink>
          <NavLink to="/research">
            Research <span>研究</span>
          </NavLink>
          <NavLink to="/methods">
            Methods <span>方法</span>
          </NavLink>
        </nav>
        <span className="header-state">
          <span className="status-dot" />
          LOCAL WORKSPACE
        </span>
      </header>
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/datasets" element={<Archive />} />
        <Route path="/studio/:sequenceId" element={<Studio />} />
        <Route path="/research" element={<Research />} />
        <Route path="/methods" element={<ProtocolPage methods />} />
        <Route
          path="*"
          element={
            <main id="main" className="page">
              <h1>未找到此页面</h1>
              <Link to="/datasets">返回数据档案</Link>
            </main>
          }
        />
      </Routes>
    </>
  );
}
export default function App() {
  return <Shell />;
}

function Overview() {
  const datasets = useDatasets();
  const sequences = useSequences();
  const available = datasets.data?.find((d) => d.id === PRIMARY_DATASET);
  const first = sequences.data?.[0];
  return (
    <main id="main" className="page overview">
      <div className="page-kicker">
        <span>COMPUTATIONAL BIOLOGY</span>
        <span>工作区 / 01</span>
      </div>
      <section className="overview-intro">
        <div>
          <div className="eyebrow accent">OBSERVE. MEASURE. MODEL.</div>
          <h1>
            从真实观测出发，
            <br />
            <span>研究形态如何演化。</span>
          </h1>
          <p className="lead">
            果蝇胚胎 in vivo 激光创面闭合。
            <br />
            逐帧检查实验影像、原始轮廓与数据质量，
            <br className="wide-only" />
            为可复现的局部动力学预测建立依据。
          </p>
          <Link to="/datasets" className="primary-link">
            进入数据档案 <Arrow />
          </Link>
          <div className="overview-footnote">
            <span className="status-dot" />
            M5 · 观测与形态推理 <span className="divider-text">/</span> 本地实验工作区
          </div>
        </div>
        <div className="specimen">
          <div className="specimen-header">
            <span className="eyebrow">OBSERVED / 实测显微影像</span>
            <span className="mono">128 × 128 px</span>
          </div>
          <QueryState
            pending={sequences.isPending}
            error={sequences.error}
            empty={!first}
            retry={() => {
              void sequences.refetch();
            }}
          >
            <Link
              to={`/studio/${first?.id}`}
              className="specimen-image"
              aria-label={`浏览序列 ${first?.id}`}
            >
              <img
                src={first ? frameUrl(first.id, 0, 'observed') : undefined}
                alt={`${first?.id ?? ''} 第0帧真实显微影像`}
              />
              <span className="image-corner top-left" />
              <span className="image-corner bottom-right" />
            </Link>
            <div className="specimen-caption">
              <span>
                <strong>{first?.id}</strong> <span className="muted">FRAME 000</span>
              </span>
              <Link to={`/studio/${first?.id}`}>
                打开工作台 <Arrow />
              </Link>
            </div>
          </QueryState>
        </div>
      </section>
      <section className="overview-ledger">
        <div className="section-index">01 / AVAILABLE NOW</div>
        <div>
          <h2>真实数据与可追溯的形态预测</h2>
          <p>
            已下载的序列保留原注释和逐帧
            QC；工作台加载已注册模型预测未来轮廓。来源、划分与未知元数据随观测一起呈现，灰度原帧不冒充生成影像。
          </p>
        </div>
        <dl className="ledger-stats">
          <div>
            <dt>本地序列</dt>
            <dd>
              {available?.sequence_count ?? '—'}
              <small>SEQUENCES</small>
            </dd>
          </div>
          <div>
            <dt>已解析帧</dt>
            <dd>
              {available?.frame_count?.toLocaleString() ?? '—'}
              <small>FRAMES</small>
            </dd>
          </div>
        </dl>
      </section>
      <section className="overview-bottom">
        <div>
          <span className="eyebrow">RESEARCH QUESTION</span>
          <h2>局部规则，能否可靠预测远期形态？</h2>
          <p>
            研究观测轮廓条件下的形态预测。以相同输入、目标和预算比较经典基线与 NCA，并如实记录失败。
          </p>
          <Link to="/research" className="text-link">
            研究协议 <Arrow />
          </Link>
        </div>
        <div>
          <span className="eyebrow">EVIDENCE BEFORE TRAINING</span>
          <h2>保留边界，也保留不确定性。</h2>
          <p>
            原始官方划分未知；本项目采用独立的
            morpholab-split-v1。派生区域与原注释分别标识，不冒充人工填充真值。
          </p>
          <Link to="/methods" className="text-link">
            方法与限制 <Arrow />
          </Link>
        </div>
      </section>
    </main>
  );
}

function Archive() {
  const datasets = useDatasets();
  const [datasetId, setDatasetId] = useState(PRIMARY_DATASET);
  const [search, setSearch] = useState('');
  const [split, setSplit] = useState('all');
  const selected = datasets.data?.find((d) => d.id === datasetId);
  const sequences = useSequences(selected?.local_available ? datasetId : '');
  const records =
    sequences.data?.filter(
      (s) =>
        s.id.toLowerCase().includes(search.toLowerCase()) &&
        (split === 'all' || s.project_split === split),
    ) ?? [];
  return (
    <main id="main" className="page archive">
      <div className="page-kicker">
        <span>DATASET ARCHIVE</span>
        <span>数据档案 / 02</span>
      </div>
      <div className="page-heading">
        <div>
          <h1>
            数据档案<span className="title-period">.</span>
          </h1>
          <p>真实实验的来源、序列与逐帧质量。选择一条记录，进入科学画布。</p>
        </div>
        <span className="protocol-tag">morpholab-split-v1</span>
      </div>
      <QueryState
        pending={datasets.isPending}
        error={datasets.error}
        empty={datasets.data?.length === 0}
        retry={() => {
          void datasets.refetch();
        }}
      >
        <div className="dataset-tabs" role="group" aria-label="数据来源">
          {datasets.data?.map((d, index) => (
            <button
              key={d.id}
              onClick={() => {
                setDatasetId(d.id);
                setSearch('');
                setSplit('all');
              }}
              aria-pressed={datasetId === d.id}
            >
              <span className="mono muted">0{index + 1}</span>
              <strong>
                {d.id === PRIMARY_DATASET
                  ? '果蝇胚胎 · 激光创面'
                  : d.biology_domain.includes('static')
                    ? 'BBBC019 · 静态图像'
                    : 'GigaDB · 体外划痕'}
              </strong>
              <span className={d.local_available ? 'source-status available' : 'source-status'}>
                {d.local_available ? '本地已获取' : '候选来源'}
              </span>
            </button>
          ))}
        </div>
        <div className="archive-source">
          <div>
            <span className="eyebrow">
              {selected?.local_available ? 'IN VIVO / DROSOPHILA EMBRYO' : 'SOURCE RECORD'}
            </span>
            <h2>{selected?.name}</h2>
            <p>
              {selected?.local_available
                ? '原始影像与骨架化创面轮廓。QC失败帧保留可见，训练窗口按协议排除。'
                : '该来源尚未完成本地获取，不提供序列浏览。不同生物体系独立审计与评价。'}
            </p>
          </div>
          <div className="source-facts">
            <a href={selected?.source_url} target="_blank" rel="noreferrer">
              {selected?.doi ?? '官方记录'} ↗
            </a>
            <span>{selected?.license ?? '许可未核实'}</span>
            <Link to="/research">模型评估与研究报告 ↗</Link>
          </div>
        </div>
        {selected?.local_available ? (
          <>
            <div className="table-toolbar">
              <div className="search-field">
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  width="16"
                  height="16"
                  fill="none"
                  stroke="currentColor"
                >
                  <circle cx="10" cy="10" r="6" />
                  <path d="m15 15 5 5" />
                </svg>
                <input
                  aria-label="搜索序列"
                  placeholder="搜索序列编号…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>
              <label className="split-filter">
                本项目划分{' '}
                <select value={split} onChange={(e) => setSplit(e.target.value)}>
                  <option value="all">全部划分</option>
                  <option value="train">训练集</option>
                  <option value="validation">验证集</option>
                  <option value="test">留出集</option>
                </select>
              </label>
              <span className="mono record-count">{records.length} RECORDS</span>
            </div>
            <QueryState
              pending={sequences.isPending}
              error={sequences.error}
              retry={() => {
                void sequences.refetch();
              }}
            >
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>序列 / SEQUENCE</th>
                      <th>影像</th>
                      <th className="number">帧数</th>
                      <th>本项目划分</th>
                      <th className="number">有效 QC 帧</th>
                      <th>官方划分</th>
                      <th>
                        <span className="sr-only">打开</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.map((s) => (
                      <tr key={s.id}>
                        <td>
                          <Link to={`/studio/${s.id}`} className="sequence-link">
                            {s.id}
                          </Link>
                        </td>
                        <td className="mono muted">
                          {s.width} × {s.height}
                        </td>
                        <td className="number mono">{s.frame_count}</td>
                        <td>
                          <span className={`split-badge ${s.project_split}`}>
                            {splitLabel(s.project_split)}
                          </span>
                        </td>
                        <td className="number mono">
                          {s.qc_valid_count} <span className="muted">/ {s.frame_count}</span>
                        </td>
                        <td className="muted">{s.official_split ?? '未知'}</td>
                        <td>
                          <Link
                            to={`/studio/${s.id}`}
                            aria-label={`打开序列 ${s.id}`}
                            className="row-arrow"
                          >
                            <Arrow />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {records.length === 0 && (
                <div className="query-state">
                  <h2>没有匹配的序列</h2>
                  <button
                    onClick={() => {
                      setSearch('');
                      setSplit('all');
                    }}
                  >
                    清除筛选
                  </button>
                </div>
              )}
            </QueryState>
            <p className="table-note">
              源序列作为独立分组的代理；实际采集批次与生物独立性未知。项目划分不等同于原作者官方划分。
            </p>
          </>
        ) : (
          <div className="unavailable">
            <span className="hollow-dot" />
            <div>
              <h3>尚未获取本地文件</h3>
              <p>当前仅保留来源记录。此处不展示模拟序列或未经审计的影像。</p>
            </div>
          </div>
        )}
      </QueryState>
    </main>
  );
}

function ProtocolPage({ methods = false }: { methods?: boolean }) {
  const datasets = useDatasets();
  return (
    <main id="main" className="page protocol-page">
      <div className="page-kicker">
        <span>{methods ? 'METHODS & EVIDENCE' : 'RESEARCH NOTEBOOK'}</span>
        <span>{methods ? '方法与证据 / 04' : '研究记录 / 03'}</span>
      </div>
      <div className="page-heading">
        <div>
          <h1>{methods ? '观测、注释与推导。' : '让假设接受检验。'}</h1>
          <p>
            {methods
              ? '明确每一层数据的含义，是比较模型之前的工作。'
              : '已完成12次真实训练与冻结test评价；完整多指标和失败案例见研究记录。'}
          </p>
        </div>
      </div>
      <div className="protocol-layout">
        <article>
          {methods ? (
            <>
              <section>
                <span className="section-index">01 / OBSERVED</span>
                <h2>真实影像与原注释</h2>
                <p>
                  观察对象是果蝇胚胎 in vivo
                  激光创面闭合。浏览器中的灰度图来自实际显微序列；ANNOTATION
                  为发布者提供的骨架化薄创面轮廓，不是填充区域真值。图像为显示进行转换，原始 uint16
                  文件保留。
                </p>
              </section>
              <section>
                <span className="section-index">02 / DERIVED TARGET</span>
                <h2>派生形态，需要质量门槛</h2>
                <p>
                  ADR-0001
                  确定的任务为观测轮廓条件下的形态预测。只有单一、不触边的可靠闭轮廓可用于填洞派生区域，再生成有符号距离场。失败注释不补线、不隐藏；包含失败帧的训练窗口排除，时间轴不压缩。
                </p>
                <p>
                  派生区域的 IoU/Dice 仅衡量派生区域一致性。它不能被描述为原始人工填充 mask
                  的准确度。
                </p>
              </section>
              <section>
                <span className="section-index">03 / LIMITATIONS</span>
                <h2>未知，仍然是数据的一部分</h2>
                <p>
                  包内为62条序列，而网页与论文报告61条；原作者文件级划分与排除依据无法取得。官方
                  split 保持未知。本项目独立协议固定45训练、12验证、5留出，不冒称论文复现。
                </p>
                <p>
                  逐帧时间和物理标尺尚未核实，界面只显示 frame 与
                  pixel。发布者报告的一分钟采样不等于每一帧的已核实时间。
                </p>
              </section>
              <section>
                <span className="section-index">04 / RELATED WORK</span>
                <h2>相邻研究，决定比较边界</h2>
                <p>
                  Backová 等 ISBI 2023 已在同体系进行 VQ-VAE + Transformer
                  视频预测。本项目当前形态任务与其整帧视频任务不同，不能直接比较成绩。NCA
                  局部规则和再生能力也属于已有研究。
                </p>
                <a
                  className="text-link"
                  href="https://danifranco.github.io/files/2023/biofisika/10230571.pdf"
                  target="_blank"
                  rel="noreferrer"
                >
                  ISBI 2023 作者论文 ↗
                </a>
                <br />
                <a
                  className="text-link"
                  href="https://distill.pub/2020/growing-ca/"
                  target="_blank"
                  rel="noreferrer"
                >
                  Growing Neural Cellular Automata ↗
                </a>
              </section>
            </>
          ) : (
            <>
              <section>
                <span className="section-index">01 / QUESTION</span>
                <h2>局部共享规则的长期预测能力</h2>
                <p>
                  给定合法历史轮廓，以相同输入、目标、网格、时间长度和预算，比较经典机制、简单时序网络与基础
                  NCA。观察远期误差、数值稳定性及失败模式；稳定但停止变化不算成功。
                </p>
              </section>
              <section>
                <span className="section-index">02 / PROTOCOL</span>
                <h2>固定协议，保留负结果</h2>
                <p>
                  初始观测 L=4 frames；候选预测 H=4/12/24 frames。实验使用完整连续且全部通过 QC
                  的窗口；序列和裁剪不得跨划分。所有归一化统计只由训练集拟合。
                </p>
                <p>
                  模型、预算、多 seed、配置和失败标准已由ADR冻结。每次实验记录 Git SHA、数据及权重
                  hash、环境与实际预算。
                </p>
              </section>
              <section>
                <span className="section-index">03 / EXPERIMENTS</span>
                <h2>尚无训练结果</h2>
                <p>
                  目前没有
                  checkpoint、评估分数或有效模型对比。不展示占位曲线。下一步先完成真实数据到可复现基线的计算链，再研究
                  NCA 与最小约束消融。
                </p>
              </section>
            </>
          )}
        </article>
        <aside>
          <ModelState />
          <SourceDetails compact dataset={datasets.data?.find((d) => d.id === PRIMARY_DATASET)} />
          <div className="protocol-note">
            <span className="eyebrow">RESEARCH BOUNDARY</span>
            <p>模型内虚拟场不是药物剂量或真实生物因果干预。此阶段不提供虚拟干预功能。</p>
          </div>
        </aside>
      </div>
    </main>
  );
}
