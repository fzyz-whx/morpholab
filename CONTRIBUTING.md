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
uv run --locked python scripts/export_openapi.py --check
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend api:check
pnpm --dir frontend lint
pnpm --dir frontend format:check
pnpm --dir frontend typecheck
pnpm --dir frontend test
pnpm --dir frontend build
pnpm --dir frontend test:e2e
```

Linux浏览器fixture先安装Playwright Chromium。真实E2E需实际数据、预处理、权重与worker，不能用fixture结果代替。
提交说明应列出实际命令、通过/失败/跳过和未验证项；不要只写“测试通过”。

## API契约变更

数据与预测主链使用Pydantic `response_model`；后端模型是请求/响应契约的依据。修改契约后，先导出真实应用的 [OpenAPI快照](docs/architecture/openapi.json)，再生成前端类型：

```sh
uv run --locked python scripts/export_openapi.py
pnpm --dir frontend api:generate
uv run --locked python scripts/export_openapi.py --check
pnpm --dir frontend api:check
```

[前端生成脚本](frontend/scripts/api-types.mjs)使用openapi-typescript 7.13与TypeScript 5.9.3生成 [api.d.ts](frontend/src/generated/api.d.ts)，不要手改生成产物。Python CI拒绝与实际应用不符的OpenAPI快照，前端CI拒绝与快照不符的类型。相关模型、快照与生成类型应在同一工作单元内审查；不要用手写宽泛类型绕过响应约束。

预测结果JSON只传轮廓、面积、指标和图像URL/SHA256，不再嵌入 `region`/`target_region` 像素数组；图像资产与Research公开图必须遵守hash与白名单校验。所有预测JSON，包括经典基线，统一标记 `MODEL_PREDICTION`；派生目标为 `DERIVED_ANNOTATION`，UI图例为 `PREDICTION`。详见[API契约](docs/architecture/api.md)与[作业恢复边界](docs/architecture/prediction-jobs.md)。

新作业记录Git/dirty、实现源码hash及环境，API与worker核对执行身份；旧历史的可选 `implementation:null` 保持未知。修改实现文件后重启API和worker再验收。心跳失效、进程自动重启与作业恢复是不同证据：恢复验证应记录实际job状态和图像资产，不能只检查HTTP200或监督进程已启动。服务维护不得改写正式ML结果。

## 研究变更

明确原标签与派生目标。未知物理尺度/时间保持null，同序列和裁剪不得跨split。test不用于选参数、seed或漂亮截图。
改变数据域、监督目标、控制解释或许可边界前先写ADR并讨论；新实验应有独立协议版本，保留旧负结果。
提出模型改进时提供匹配输入、训练与评价预算、多个seed、逐序列指标和失败案例；seed不是独立生物样本。

一个有意义单元一条可审查commit，检查→测试→commit→立即push→核对live远端SHA。推送失败先解决同步，不累积新提交。
公开历史用修复或revert更正，不强推美化。外部贡献者在自己的fork/分支提交PR，避免直接推主分支。
PR描述问题、最终行为、证据和局限；不提交令牌、本机路径、论文截图或许可不明样本。
