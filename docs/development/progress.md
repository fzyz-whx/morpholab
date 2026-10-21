# 开发记录

## M-1.1 · 项目公开起点 · 2026-10-21

- 完整读取并保存总任务书 v0.2，确认空目录，无既有仓库或嵌套仓库。
- 已核对 Git 2.45、gh 2.101、Python 3.12.10、Node 24.18.0、uv 0.11.3、pnpm 11.22.0；工具与授权均可用。未改全局配置和同级项目。
- 首版 README、AGENTS、愿景、路线图、质量与 Git 协议、MIT 源码许可证已建立。Markdown 本地链接和本机路径检查通过，暂存差异检查通过。
- 公开仓库：[fzyz-whx/morpholab](https://github.com/fzyz-whx/morpholab)。首提交 [`a4a9aa1b694682594be7898770811586d511a5e9`](https://github.com/fzyz-whx/morpholab/commit/a4a9aa1b694682594be7898770811586d511a5e9)，push 成功后通过 `git ls-remote` 核对相同 SHA。
- 首次 push 被已有 HTTPS→SSH 全局改写导向不具备本仓库权限的 deploy key；暂停后续工作，仅对当前仓库设置更具体的 HTTPS 映射，使用现有 gh 授权成功推送。全局配置未变。
- Issues [#1 数据审计](https://github.com/fzyz-whx/morpholab/issues/1)、[#2 研究协议](https://github.com/fzyz-whx/morpholab/issues/2)、[#3 工作台验收](https://github.com/fzyz-whx/morpholab/issues/3) 已创建。
- 模型未训练，实验未评估，无软件 UI 截图。下一工作单元为最小 CI 与质量工具，再推进真实下载审计。

## M-1.2 · 离线质量工具与最小 CI · 2026-10-21

- 建立根 uv 项目与锁文件，仅安装当前审计所需科学计算、类型与开发依赖，尚未安装训练框架。
- 实现公开文件/本地文档链接检查和实时远端 SHA 核对工具，配置 Windows / Ubuntu 最小权限 CI。
- 本地 `uv sync --locked --python 3.12`、重点 ruff lint/format、8 项质量工具测试、重点 mypy、公开文件检查均通过；同步工具实时核对首提交通过。
- 此记录所在提交是本工作单元；后续阶段记录引用其 SHA 与远端 CI 结果，不预写尚未运行的远端结论。

## M0.1 · 可校验公开下载与目录证据 · 2026-10-21

- 前项质量提交 [`4146e6c39b3446c81f5ee19f5d899c84ac6a28b1`](https://github.com/fzyz-whx/morpholab/commit/4146e6c39b3446c81f5ee19f5d899c84ac6a28b1) 已立即 push 并核对；[GitHub Actions](https://github.com/fzyz-whx/morpholab/actions/runs/39587179405) 的 Windows 和 Ubuntu 均成功，M-1 通过。
- 实现标准库下载器：安全续传、超时/次数/总时间边界、发布MD5与本地SHA256、失败非零与状态留档；只检查ZIP目录，不执行数据内代码。
- 真实下载198,715,081 bytes，207.796秒，发布MD5匹配。记录62对TIFF与网页61条不一致，没有猜测官方split。
- 新增下载器13项离线测试；连同此前8项质量工具测试共21项。后续内容审计与训练验收尚未完成。

## M0.2 · 相邻工作与可证伪问题 · 2026-10-21

- 下载工具提交 [`72877cd806ee7d2bad996616f6301214b5f97ff1`](https://github.com/fzyz-whx/morpholab/commit/72877cd806ee7d2bad996616f6301214b5f97ff1) 已立即 push 并核对实时远端 SHA。
- 完成六项相邻工作矩阵，特别区分 Backová 同数据视频预测与 NOLTA 2026 仅录用摘要证据；明确本项目不能以概念组合宣称首创。
- 候选假设限定为相同观测/数据/预算下的长期稳定性，以及单一状态更新幅度惩罚的消融；未决定监督目标、未训练、未评估。
- 依据作者论文、出版社与官方数据源阅读核验；文档链接/公开文件检查及暂存差异检查通过，本单元没有新增程序行为。

## M0.3 · 可验证时序数据契约 · 2026-10-21

- 相邻工作提交 [`69017c6abbce87f5f5fea5cd789ff7c422db9891`](https://github.com/fzyz-whx/morpholab/commit/69017c6abbce87f5f5fea5cd789ff7c422db9891) 已立即 push 并核对实时远端 SHA。
- 新增可安装的纯计算包及 Frame / Sequence / Collection 契约，拒绝未知注释、错序/缺帧、尺寸变化、同实验跨split、路径越界与实际文件hash不匹配。物理时间/标尺保持可空，源序列代理分组不冒称生物独立。
- 根项目从仅脚本环境演化为实际可编辑安装包；`uv sync --locked` 与安装后 import 通过，重点 mypy 三个源文件通过。
- 当前69项测试通过，1项真实symlink测试因本机创建权限不足明确跳过；另有无需该权限的解析越界测试通过。未重跑训练或声称数据闸门已全部完成。

### M0.3 修复记录

契约提交 `571b1c8c7f4ac2299c36bebebc44bbd264d4faf0` 已即时 push 并核对，但提交时发现根 `.gitignore` 的 `data/` 同时匹配计算包源码目录，导致源码未入暂存；本机测试依赖未跟踪文件，未揭示检出缺失。立即把数据忽略限定为根 `/data/` 与 `/artifacts/`，以新增修复提交补齐源码；不重写已公开历史。后续明确检查每次暂存返回值，并以干净检出验证包安装和测试。

## M0.4 · 全量内容审计与真实QA · 2026-10-21

- 修复提交 [`f999ff0bc0d344770e9d7bff00af32966d219940`](https://github.com/fzyz-whx/morpholab/commit/f999ff0bc0d344770e9d7bff00af32966d219940) 已即时push、远端SHA一致，[双平台CI](https://github.com/fzyz-whx/morpholab/actions/runs/39588182065)成功。此前漏源码提交的CI确实失败，保留历史。
- 从已提交HEAD另做干净本地clone，锁定安装、69 passed/1 symlink权限skip、重点mypy、文档检查均通过，确认不依赖未跟踪源码。
- 全量读取62条/7229帧；实际查看两条各六连续时间点原图/标注叠加；样本PNG逐像素回读一致。薄轮廓非填充mask，7210帧严格闭曲线候选，26帧触边，严格闭曲线且不触边共7184帧。
- 发布元数据审计摘要和CC BY署名说明，不发布原始大影像；源数据完整性、解压与TIFF解码边界、缺配对/尺寸/编码/重复/导出等有离线测试。
- 官方61/44/12/5文件映射未找到，作者项目页404；未删序列凑数、未猜官方split。下一单元为明确派生目标与独立实验协议的ADR。

## M0 闸门 · 2026-10-21

- 全量审计提交 [`468478ce4f9b2e2e0f542ac3021ad79a728eb037`](https://github.com/fzyz-whx/morpholab/commit/468478ce4f9b2e2e0f542ac3021ad79a728eb037) 已即时push并核对。
- ADR-0001冻结主域、可靠闭轮廓派生区域/距离场、严格QC与明确区别于作者原split的本项目45/12/5协议。没有删序列凑数，没有将薄线当填充GT，没有改变为面积单任务。
- M0数据与文献闸门通过，未解决限制继续公开。后续可推进真实浏览器设计系统及可复现数据管线；正式训练仍以模型/预算协议为前提。

## 数据管线 · 2026-10-21

- ADR提交 [`a6ceb162a651a3571533b505c16c16e3c5a81ff1`](https://github.com/fzyz-whx/morpholab/commit/a6ceb162a651a3571533b505c16c16e3c5a81ff1) 已即时push、远端核对，双平台CI通过。
- 实现严格QC、轮廓派生区域/SDF、源帧保留、冻结45/12/5新协议、窗口有效性与NPZ/hash清单；29项离线测试通过。
- 真实全量运行62条/7229帧，7183有效；最近邻降采样额外使1帧区域消失，明确拒绝。幂等重跑hash一致，逐文件安全回读成功；有限近重复筛查0候选，未宣称生物独立已证明。
- 与M1并行提供真实数据基础，不将此项称为模型训练或M2基线评估完成。

## M1.1 · 本机只读数据API · 2026-10-21

- 数据管线提交 [`37f62ddcfd127e1db480789abb633b3877a4776c`](https://github.com/fzyz-whx/morpholab/commit/37f62ddcfd127e1db480789abb633b3877a4776c) 已立即push并核对。
- 提供dataset/sequence/frame/health，统一来源/空模型ID/UTC信封与安全错误，实际读取前校验源ZIP，有限LRU，不提供任意路径或写操作。
- 后端27项离线TestClient测试通过；独立启动HTTP进程后实测62序列、7183有效帧、WH01原始轮廓叠加PNG=128×128；此项与ASGI测试分开记录。
- 新版Starlette提示httpx测试适配弃用，按已安装源码支持切换到httpx2，重跑27项测试通过且无该警告。根pytest已收集backend/tests。
- UI真实浏览器已开始核验，1280×720默认图像裁切仍在修复；未将M1视觉验收标为通过。
