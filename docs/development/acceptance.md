# 验收证据与执行边界

本记录区分离线fixture、真实训练、独立HTTP进程、实际浏览器、新克隆与远端CI。
它不把文件存在、请求成功或HTTP200单独当作项目验收。

## 阶段与可查证来源

| 阶段 | 证据 |
|---|---|
| M-1 | [首提交a4a9aa1](https://github.com/fzyz-whx/morpholab/commit/a4a9aa1b694682594be7898770811586d511a5e9)、真实公开仓库、逐提交同步记录 |
| M0 | [全量审计](../research/data-audit.md)、来源checksum、62/61差异、薄轮廓定义、许可与独立协议ADR |
| M1 | [设计审查](../design/reviews/2026-10-21-m1.md)、真实PNG/图层/键鼠/时间轴/QC和双尺寸适配 |
| M2 | [validation基线](../research/baselines-validation-v1.md)、严格管线和负结果 |
| M3 / M4 | [12次训练预算](../research/results/training-budget-v1.json)、[冻结test](../research/forecast-results-v1.md)、3seed/消融/失败/模型卡 |
| M5 | [持久作业](../architecture/prediction-jobs.md)、[真实工作台](../design/reviews/2026-10-22-m5.md)、真实作业恢复与指标链 |
| M6 | [条件降级ADR](../project/decisions/ADR-0004-defer-control-and-bound-reliability.md)，没有虚拟控制完成主张 |
| M7 | 下述新克隆、依赖锁、CPU复算、全矩阵复训、CI及发布检查；当前发布验收进行中 |

## 本机与真实链

主目录集成源码`3e44d2d9fae46bd82c194377208f9bd837c06b73`：

- Python完整套件261 passed、1 skipped，skip为Windows创建符号链接权限；Ruff检查/格式与6个重点模块mypy通过。
- 前端lint、格式、严格类型、10项组件fixture、生产构建通过；离线浏览器fixture1 passed。
- 生产服务器实际数据E2E5 passed：62序列来源/图层、键盘/播放/QC、双桌面适配、真实NCA24步作业与刷新历史恢复、冻结研究报告。
- 实际HTTP作业为WH01 L4/H24，独立CPU worker完成；每lead源帧、contour/region、metrics与数据/权重hash均取得，不只看202。
- 新增权重安装器7项合成安全检查通过；12权重2,685,719字节ZIP与39个成员哈希均固定，离线新目录安装通过。
- 单项截图复核曾出现断言已通过但Edge退出拖至3.2分钟；没有当作命令已结束。加入120秒全局测试上限并关闭headless测试的GPU依赖后，完整5条真实链7.2秒结束；具体退出延迟原因尚未确认，未把该测试环境调整解释为产品推理提速。

## 全新克隆核验

实际从公开GitHub完整clone，源码`666c05b0f15a9714b6afc7008c7ffb7901207085`，新建项目venv与node_modules，未复用原venv。
依赖通过本机uv/pnpm内容缓存安装；这验证锁定依赖和全新环境，不冒称全部轮子重新从互联网下载。

```sh
uv sync --locked --extra cpu --extra reports
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
python scripts/download_models.py --archive <已验证本地发布包>
python -m pytest -q
ruff check .
ruff format --check .
mypy
python scripts/check_docs.py
```

实际结果：268 passed、1 Windows symlink skip；Ruff/格式、6模块mypy、文档、前端生产构建均通过。
此处模型安装使用与发布附件相同哈希的本地bundle，尚不能当作公开URL可下载证据。
数据评价明确只读复用原先完整校验的源清单/NPZ缓存，没有冒称新下载199MB或独立重新标注。

同一干净克隆用CPU重新评分全部12检查点、全部test主窗口及L敏感性，耗时71.578秒。
主表144行的七项聚合指标与原CUDA正式结果最大绝对差为0；这证明本次离散区域指标一致，不承诺所有硬件的浮点逐位相同。
正式原结果始终保留CUDA/a83ed4d来源，不用CPU运行替换原始元数据。

完整12-run CUDA复训已在该干净新克隆单独新目录启动；完成情况与比较结果待实际核对，未预写成功。

## 远端CI与同步

- [39627733576](https://github.com/fzyz-whx/morpholab/actions/runs/39627733576)：早期神经实现三项成功。
- [39631839108](https://github.com/fzyz-whx/morpholab/actions/runs/39631839108)：评价fixture曾在Ubuntu浅克隆历史与Windows缺可选Torch处失败，保留记录。
- [39694536461](https://github.com/fzyz-whx/morpholab/actions/runs/39694536461)：修复fixture用当前可用revision与importorskip后，三项成功。
- [39696006055](https://github.com/fzyz-whx/morpholab/actions/runs/39696006055)：主分支集成后Windows、Ubuntu CPU+reports、前端+Chromium fixture三项成功。

后期push事件未产生预期自动运行记录，原因未确认；使用已提交的workflow_dispatch手动触发并核对实际head，不能称自动触发正常。
每条开发提交均立即push并以live远端SHA核对；失败先修同步，不补造历史。完整过程见[progress](progress.md)。

## 尚未验证或不在版本范围内

没有独立生物重复、跨域验证、准确物理时间/尺度、临床适用或干预因果证据；没有全面第三方安全审计。
Linux由远端CI验证代码/CPU fixture与Chromium synthetic链，真实显微数据与真实checkpoint的浏览器链在本机Windows执行。
本版不声明已验证公网或多用户部署。正式Release与公网权重URL需要在最终发布步骤实际核验。
