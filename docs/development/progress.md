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
