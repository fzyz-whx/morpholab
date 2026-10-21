# MorphoLab · 形态实验室

研究真实显微时序中的创面闭合，比较局部神经更新规则与经典动力学、时序网络的预测行为。

**Research prototype · 开发中。** M0已通过：完整校验并解析62条、7,229帧真实创面时序，明确薄轮廓派生形态目标与独立划分协议。官方划分映射仍未知。模型未训练，实验未评估，Web 工作台尚未实现。

## 研究问题

给定创面闭合过程的前几个观测时间点，具有共享局部更新规则的神经细胞自动机（Neural Cellular Automata, NCA）能否预测后续形态，并在长期滚动预测中保持稳定？我们将通过固定实验级划分、朴素基线和失败案例评价它，而不预设 NCA 一定更好。

优先审计的数据是 **果蝇胚胎 in vivo 激光创面闭合**，不是体外细胞划痕，也不是临床皮肤伤口。NCA 的网格单元是计算状态，不等同于真实细胞。后期可能加入的干预仅为模型内虚拟实验，不支持现实生物因果或治疗结论。

## 开发状态

| 阶段 | 当前状态 | 可检查的交付 |
|---|---|---|
| M-1 仓库启动 | 已完成 | 公开仓库、工作协议、Windows / Ubuntu CI 通过 |
| M0 数据与相关工作审计 | 已通过，限制保留 | 全量解析、来源清单、本地QA、派生目标与独立协议ADR |
| M1 设计系统与真实数据浏览 | 未实现 | 无产品截图 |
| M2–M4 数据管线、模型与实验 | 未实现 | 未训练、未评估 |
| M5–M7 软件闭环与发布 | 未实现 | 无可运行 Web 产品 |

此时没有可演示的预测功能。真实运行界面、原创方法图及科研结果图将随对应功能落地逐步加入。

## 方法与证据边界

计划比较 Persistence、经典边界动力学、小型 ConvGRU/ConvLSTM、基础 NCA，以及有明确假设的最小改进。监督目标和指标必须由数据标签的实际语义决定：骨架线不能直接当作区域真值计算 IoU。

当前任务明确为**历史轮廓条件下的形态预测**，原始显微图像用于浏览与对齐；不是由灰度图自动分割或生成未来显微纹理。[ADR-0001](docs/project/decisions/ADR-0001-observed-domain-target-and-split.md)规定闭轮廓派生区域、严格QC及45/12/5的独立协议，未声称恢复作者44/12/5。

创面视频预测与 NCA 外部信号响应均已有研究；本项目不将这些概念组合称为创新。相关工作、资源预算和对照协议将先于正式训练明确。

```mermaid
flowchart LR
  A[公开数据与授权] --> B[下载审计与来源清单]
  B --> C[预处理与实验级划分]
  C --> D[基线与 NCA 对照]
  D --> E[误差分析与可追溯产物]
  E --> F[Web 科研工作台]
```

上图表示目标架构，当前已实现项目质量工具与可校验下载器。

## 从这里开始

- [项目愿景](docs/project/vision.md)：用户、科学问题与不做的范围。
- [开发路线图](docs/project/roadmap.md)：阶段依赖与验收闸门。
- [数据审计](docs/research/data-audit.md)：网页描述、实际文件与尚未解决问题。
- [相邻工作](docs/research/related-work.md)与[候选假设](docs/research/hypotheses.md)：已有成果、重复风险及可证伪问题。
- [数据契约](docs/architecture/data-contract.md)：来源、连续性、分组、编码文件 hash 与路径边界。
- [总任务书 v0.2](docs/project/master-plan-v0.2.md)：完整研发契约。
- [质量规范](docs/development/quality.md)与 [Git 工作协议](docs/development/git-workflow.md)。

本机已核对 Python 3.12.10、Node 24.18.0、uv 0.11.3、pnpm 11.22.0。以下 CPU 命令已执行；当前无需安装 PyTorch 或使用商业模型 API：

```sh
uv sync --locked --python 3.12
uv run --locked python scripts/check_docs.py
uv run --locked pytest -q tests/test_check_docs.py tests/test_verify_remote.py
uv run --locked mypy
```

下载真实数据（约 199 MB，需要网络；后续自动验证缓存）：

```sh
uv run --locked python scripts/download_data.py
uv run --locked python scripts/audit_data.py
uv run --locked pytest -q tests/test_download_data.py
```

压缩包有62对TIFF，与发布页61条描述不同。审计会生成逐帧清单、两条各六帧样本与本地轮廓叠加QA；45帧不满足严格闭曲线且不触边的规则。原图不进入Git，官方划分未知，未开始训练。

公开仓库检查会验证本地文档链接并拦截部分敏感文件模式；它不能替代人工许可和秘密审查。远端同步可运行 `uv run --locked python scripts/verify_remote.py` 实时核对，不以缓存的 origin 状态代替。

## 数据、许可与参考

- [Backova 等，Zenodo 7660424](https://doi.org/10.5281/zenodo.7660424)：首选体内创面时序，API标注 CC BY 4.0，完整压缩包 MD5 已核对；标签与划分待审计。大型影像不进入 Git。
- [GigaDB 100118](https://doi.org/10.5524/100118)：不同生物域的体外划痕实验，原始下载与许可待核查，不与果蝇指标混为一组。
- [BBBC019](https://bbbc.broadinstitute.org/BBBC019)：静态图像辅助资源，不拼成伪造视频。
- [Growing Neural Cellular Automata](https://distill.pub/2020/growing-ca/)，2020：局部规则、生长与再生的既有工作。
- [Neural Cellular Automata Can Respond to Signals](https://arxiv.org/abs/2305.12971)，2023：条件响应的相邻工作。
- [Modeling Wound Healing Using Vector Quantized Variational Autoencoders and Transformers](https://cvpd.github.io/publication/backova-2023-modeling/)，ISBI 2023：本数据体系上的视频预测工作。

源码采用 [MIT License](LICENSE)。第三方数据、论文图片和模型权重遵循各自条款，源码许可证不授予它们的再分发权。

## English overview

MorphoLab is an early research software project for wound-closure morphodynamics in real microscopy time series. It will compare local neural cellular automata with classical and learned forecasting baselines, with experiment-level splits and traceable evidence. The initial domain is **in vivo Drosophila embryonic laser wounds**. No model has been trained or evaluated yet.
