# 数据目录与使用边界

`registry.yaml` 是来源与审计状态注册表，不包含原始影像。`reported_*` 表示发布者描述，未必已经从文件内容确认；null 表示未知。`redistribution_allowed: false` 是当前发布策略，不能被误读为所有来源均禁止再分发。

原始下载、缓存、选取样本、QA 和大型审计日志位于项目根 `artifacts/`（Git 忽略）。公开仓库仅保留工具、允许分享的清单、许可与来源说明。原始下载保持不变，转换产物单独保存并记录 hash。

优先 Zenodo 7660424。GigaDB 为独立体外数据域；BBBC019 为静态辅助资源，不能构造真实时序。所有下载与读取结果见 [数据审计](../docs/research/data-audit.md)。

依赖标签转换的指标必须在 ADR 中定义并通过 QA。即使发布者称 segmentation，也不能直接假设它是填充区域 mask。
