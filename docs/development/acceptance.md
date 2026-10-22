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
| M7 | 下述新克隆、依赖锁、CPU复算、全矩阵复训和CI；最终tag与公网权重下载记录见[Release附件](https://github.com/fzyz-whx/morpholab/releases/tag/v0.1.0) |

## 本机与真实链

主目录集成源码`3e44d2d9fae46bd82c194377208f9bd837c06b73`：

- Python完整套件261 passed、1 skipped，skip为Windows创建符号链接权限；Ruff检查/格式与6个重点模块mypy通过。
- 前端lint、格式、严格类型、10项组件fixture、生产构建通过；离线浏览器fixture1 passed。
- 生产服务器实际数据E2E5 passed：62序列来源/图层、键盘/播放/QC、双桌面适配、真实NCA24步作业与刷新历史恢复、冻结研究报告。
- 实际HTTP作业为WH01 L4/H24，独立CPU worker完成；每lead源帧、contour/region、metrics与数据/权重hash均取得，不只看202。
- 新增权重安装器7项合成安全检查通过；12权重2,685,719字节ZIP与39个成员哈希均固定，离线新目录安装通过。
- 单项截图复核曾出现断言已通过但Edge退出拖至3.2分钟；没有当作命令已结束。加入120秒全局测试上限并关闭headless测试的GPU依赖后，完整5条真实链7.2秒结束；具体退出延迟原因尚未确认，未把该测试环境调整解释为产品推理提速。

随后在源码`ba3a48c5db4c402470e9a98126c2b9a76fe84035`完成契约和恢复改进：

- Python完整套件302 passed、1 Windows symlink skip；前端组件14 passed，lint/格式/类型/生成契约/生产构建通过。
- 实际Edge生产服务器6条真实E2E通过：真实NCA、独立64-grid误差PNG、前一真实观测帧、鼠标原坐标、历史恢复、62序列与QC、完整Research的12run/6失败图、390移动阅读、1440/1280画布适配。
- 真实HTTP六种方法成功，结果没有JSON像素数组，PNG与源码/环境身份有hash；这些是开发链核验，记录的dirty状态不冒充正式研究。
- Windows实测读句柄占用时`os.replace`可报WinError5；原worker退出堆栈未完整保留，不能断言它是那次退出的唯一原因。添加有界重试和心跳失败隔离。
- Supervisor六项模拟进程检查通过。另真正结束自有running NCA worker，监护器更换PID后，同一job `2d49b947-0cbc-4f13-85d5-d5ae8b2effdf`恢复为succeeded，24帧和独立PNG完整，原权重hash不变。

截图复审另发现Research坐标文字对比度低、图例未排版，修复提交`2540f108ba009c2550d5e0afcf180d0d7b844b9e`。
修复包含失败图自适应宽度，未改变科学计算；生产构建、lint/格式和包含颜色/图例样式断言的6条真实E2E再次通过。
该次完整浏览器命令11.1秒实际退出，不把截图保存成功单独当通过。

## 全新克隆核验

实际从公开GitHub完整clone，起始源码`666c05b0f15a9714b6afc7008c7ffb7901207085`，新建项目venv与node_modules，未复用原venv。
依赖通过本机uv/pnpm内容缓存安装；这验证锁定依赖和全新环境，不冒称全部轮子重新从互联网下载。
本机全局Git把HTTPS改成SSH，克隆/fetch实际用了[FAQ](../FAQ.md)的命令级精确URL映射；没有改全局Git。

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

最初结果：268 passed、1 Windows symlink skip；Ruff/格式、6模块mypy、文档、前端生产构建均通过。
后来fast-forward至ba3a48c，在独立CPU环境再次运行完整检查：302 passed、1 skip，50.54秒；Ruff/格式、6模块mypy、文档、实际OpenAPI导出对比通过。
前端lint/格式/typecheck/api:check、14组件fixture和生产构建通过。再fast-forward至2540f10构建，从该克隆的独立API/worker/数据/权重执行真实E2E6 passed（12.1秒）、synthetic fixture1 passed（2.0秒）。
真实NCA24步作业另行读取并核对implementation.git_sha等于克隆HEAD、git_dirty=false，manifest与原训练相同；并非转发到原工作目录的服务。

最初评价只读复用已校验清单/NPZ；随后在克隆内独立运行download→audit→prepare。
为避免重复下载，源ZIP用已核验原件的NTFS硬链接：下载器仍刷新官方API并全量核验字节与checksum，明确返回cached=true；不称重新下载199MB。
审计重新解析62对/7229帧、重新准备全部NPZ，manifest SHA256与正式输入相同：`a04b3a66c9fb910c6f3b180e5ce22ca185e721daeacda19433fde3f82fea6ce0`。
没有独立重新人工标注。模型最初通过本地相同bundle安装；公网URL证据只由Release最终核验附件确认。

同一干净克隆用CPU重新评分全部12检查点、全部test主窗口及L敏感性，耗时71.578秒。
主表144行的七项聚合指标与原CUDA正式结果最大绝对差为0；这证明本次离散区域指标一致，不承诺所有硬件的浮点逐位相同。
正式原结果始终保留CUDA/a83ed4d来源，不用CPU运行替换原始元数据。

同一干净克隆切换已锁定CUDA extra，在独立新目录完整复训12run，每run600步，合计674.371秒。
用`torch.equal`逐张量比较best模型，并逐项比较所有600步数值history（排除elapsed_seconds）：12/12完全一致，最佳步数和validation loss亦一致。
文件checkpoint hash因Git/时间元信息不同而不同，未声称文件逐位相同。[公开逐run证据](../research/results/reproduction-v1.json)保留新权重hash和源码SHA。
原始CUDA run、模型和正式报告没有覆盖，CPU与复训证明也不保证任意硬件逐位一致。

## 远端CI与同步

- [39627733576](https://github.com/fzyz-whx/morpholab/actions/runs/39627733576)：早期神经实现三项成功。
- [39631839108](https://github.com/fzyz-whx/morpholab/actions/runs/39631839108)：评价fixture曾在Ubuntu浅克隆历史与Windows缺可选Torch处失败，保留记录。
- [39694536461](https://github.com/fzyz-whx/morpholab/actions/runs/39694536461)：修复fixture用当前可用revision与importorskip后，三项成功。
- [39696006055](https://github.com/fzyz-whx/morpholab/actions/runs/39696006055)：主分支集成后Windows、Ubuntu CPU+reports、前端+Chromium fixture三项成功。
- [39698125684](https://github.com/fzyz-whx/morpholab/actions/runs/39698125684)：双语文档与0.1.0候选版本三项成功。
- [39746878777](https://github.com/fzyz-whx/morpholab/actions/runs/39746878777)：ba3a48c契约/PNG/恢复实现，三项成功。最终tag对应CI记录随Release验收附件提供，避免把先前head的成功当作后续head成功。

后期push事件未产生预期自动运行记录，原因未确认；使用已提交的workflow_dispatch手动触发并核对实际head，不能称自动触发正常。
每条开发提交均立即push并以live远端SHA核对；失败先修同步，不补造历史。完整过程见[progress](progress.md)。

## 尚未验证或不在版本范围内

没有独立生物重复、跨域验证、准确物理时间/尺度、临床适用或干预因果证据；没有全面第三方安全审计。
Linux由远端CI验证代码/CPU fixture与Chromium synthetic链，真实显微数据与真实checkpoint的浏览器链在本机Windows执行。
本版不声明已验证公网或多用户部署。最终Release资产核验是发布后独立步骤，结果保存在Release的`release-verification.json`，含tag目标、CI和从公开URL取得的实际文件hash。
这一附件只记录实际完成的操作，不回写/改造既有源码或研究历史。
