# 需求与证据映射

依据master-plan-v0.2，最终以真实证据验收，不能以此表自我声明替代执行。发布前逐项核对[acceptance](../development/acceptance.md)。

| ID | 要求 | 实现与证据 |
|---|---|---|
| DATA-01 | 真实公开动态数据、实际下载、结构与许可 | [数据审计](../research/data-audit.md)、datasets/registry.yaml、来源hash |
| DATA-02 | 原轮廓与派生目标分开、严格QC、未知量null | [数据管线](../architecture/data-pipeline.md)、ADR-0001、数据与prepare测试 |
| DATA-03 | 保留完整时间索引与源序列分组、不借test追分 | 固定45/12/5协议、窗口/泄漏检查、完整正式run来源 |
| SCI-01 | Persistence、Classical、ConvGRU、NCA与拟议正则 | [模型定义](../architecture/forecast-models.md)、ML源码、12次真实训练 |
| SCI-02 | 多seed/horizon/输入长度、两项消融与失败 | [正式报告](../research/forecast-results-v1.md)、公开逐序列JSON、最差案例 |
| SCI-03 | 不夸大NCA/正则/域迁移/现实干预 | [局限](../research/limitations.md)、模型卡、ADR-0004 |
| ENG-01 | CPU可用、checkpoint恢复、固定配置/hash | 训练fixture、完整新clone CPU评价、12run复训对比 |
| ENG-02 | 持久作业、独立worker、取消/恢复、安全加载 | backend/app、JobQueue测试、真实HTTP作业与浏览器历史恢复 |
| ENG-03 | API有数值界限、统一来源、结构化错误 | Pydantic请求/响应、OpenAPI导出和生成类型、边界及资产hash测试 |
| ENG-04 | 版本依赖锁、跨平台检查、新clone命令可用 | uv.lock / pnpm-lock、Windows/Ubuntu/Chromium CI、clean clone记录 |
| UI-01 | 原创视觉语言、科学画布、真实来源/图层/QC | [设计规范](../design/visual-language.md)、M1/M5实际截图 |
| UI-02 | 键鼠、缩放、真实坐标/前帧参照、错误/空状态 | Studio、组件fixture、真实E2E、1440/1280及移动阅读检查 |
| UI-03 | 预测/误差/曲线/配置/失败可见、没有假按钮 | 独立PNG资产、Research完整报告、真实模型E2E |
| PUB-01 | 从首提交开始公开，每commit立即push核对 | [开发记录](../development/progress.md)、公开提交历史、live SHA记录 |
| PUB-02 | 真截图/原创图/双语/引用/许可/贡献路径 | README/CITATION/CHANGELOG/CONTRIBUTING/SECURITY、assets |
| PUB-03 | 版本与Release相符、权重来源明确、公开下载核验 | [发布说明](../releases/v0.1.0.md)、固定bundle清单、最终远端核验 |

M6控制是有条件研究扩展，本版按ADR降级，不将未实现控制算完成。论文SOTA、临床能力、动物级独立性、物理标尺、跨域泛化和公网多用户均没有完成主张。
