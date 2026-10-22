# 贡献与复现

先阅读[工作协议](AGENTS.md)、[研究协议](docs/research/experiment-protocol.md)与[局限](docs/research/limitations.md)。欢迎可复现缺陷、数据来源核查、指标边界情况、失败案例分析和有证据的界面改进。

## 开发

Python使用uv与锁文件，前端使用pnpm与锁文件；环境限本项目。API默认127.0.0.1，网页不现场训练。
计算核心位于`ml/morpholab_ml`，不得依赖HTTP或数据库。来源数据、缓存、权重与任务状态留在忽略目录，不进入PR。

```sh
uv sync --locked --extra cpu --extra reports
uv run --locked --extra cpu --extra reports pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
uv run --locked python scripts/check_docs.py
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend lint
pnpm --dir frontend format:check
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
pnpm --dir frontend test:e2e
```

Linux浏览器fixture先安装Playwright Chromium。真实E2E需实际数据、预处理、权重与worker，不能用fixture结果代替。
提交说明应列出实际命令、通过/失败/跳过和未验证项；不要只写“测试通过”。

## 研究变更

明确原标签与派生目标。未知物理尺度/时间保持null，同序列和裁剪不得跨split。test不用于选参数、seed或漂亮截图。
改变数据域、监督目标、控制解释或许可边界前先写ADR并讨论；新实验应有独立协议版本，保留旧负结果。
提出模型改进时提供匹配输入、训练与评价预算、多个seed、逐序列指标和失败案例；seed不是独立生物样本。

一个有意义单元一条可审查commit，检查→测试→commit→立即push→核对live远端SHA。推送失败先解决同步，不累积新提交。
公开历史用修复或revert更正，不强推美化。外部贡献者在自己的fork/分支提交PR，避免直接推主分支。
PR描述问题、最终行为、证据和局限；不提交令牌、本机路径、论文截图或许可不明样本。
