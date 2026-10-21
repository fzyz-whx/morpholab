# MorphoLab｜从零开发总任务书（交给 Codex 执行）

> **文档性质**：项目章程 + 产品需求 PRD + 软件需求 SRS + 技术设计草案 + 科研方案 + GitHub 工作协议 + UI/README 设计规范 + 阶段验收表。  
> **版本**：v0.2 / 2026-10-21。**执行优先级**：本文 > 已批准的 ADR > 其他说明；遇到事实性冲突必须核实并记录，不得凭空补齐。  
> **项目名**：MorphoLab；建议仓库名：`morpholab`；中文名：**形态实验室**。  
> **执行者**：Codex（负责研究调研、编码、测试、文档、Git/GitHub 提交推送）；**项目负责人**：本科生用户（负责最终取舍、科研假设、重要范围变更和验收）。  
> **当前任务**：先把真实项目从空仓库一步步做出来；**现场演示视频、讲解稿、发布宣传物不是前期优先级**。但是从第一阶段起必须建设高水准的前端设计系统和 GitHub README。  
> **特别要求**：**每生成一个本地 Git commit，就必须立即成功推送到 GitHub 对应远程分支，并验证 SHA 一致；不允许积累一堆本地提交最后才推送。**

---

## 00｜Codex，先理解你接手的究竟是什么

你不拥有任何先前对话上下文。不要假设已存在完整数据、模型、页面、GitHub 仓库或已训练权重。你接收到的这份文档就是项目的完整上下文与第一版执行契约。以下不是供你“自由发挥”的点子集，而是具体研发任务；你必须从空目录组织真实、可验证、可提交的工程。

### 00.1 三句话理解项目

**MorphoLab 是一个以真实生物时间序列为依据、研究组织创面闭合形态动力学的开源科研软件。** 它学习真实显微图像中“局部结构如何随时间变化”的规律，重点探索由卷积网络定义局部状态更新规则的 **Neural Cellular Automata，NCA，神经细胞自动机**，以及在长期预测、扰动和有限控制条件下的行为。最终以一个成熟、极具设计感的交互式 Web 工作台，让人查看原始影像、预测未来边界、分析误差与执行**模型内的虚拟干预**。

它**不是** AI 聊天平台、不是人体临床伤口评估工具、不是把现成 NCA emoji 生长项目换皮、不是单纯的显微图像分类器，更不是一套只好看却没有真实算法的 Dashboard。

### 00.2 项目的真实使用故事（请先在脑中建立产品画面）

一位研究者打开 MorphoLab，在数据浏览器中选择“果蝇胚胎创面闭合 001”。屏幕中央显示真实显微图像、分割掩膜及随时间变化的创面轮廓。研究者选择前 10 帧作为观测，要求模型预测后面 10 帧。程序加载已经训练好的模型，展示每个未来时间点的预测轮廓，并与被隐藏的真实后续影像逐帧比较；右侧显示面积变化曲线、重叠率及边界误差。研究者再打开一个明确标为 **Virtual / In-silico** 的实验场景，在局部施加抽象阻力场，比较“没有干预”和“有干预”的模型演化差异。科研模式中还可以看到原始数据的来源、实验级训练/测试拆分、基线模型和消融结果。

**现阶段不要求完成以上所有交互。** 这个故事定义我们最终要交付的软件，不是要求你第一轮就把每个页面写成假按钮。早期先做真实数据链、可验证算法、稳定工程骨架和高质量设计系统；其余交互按里程碑逐步接入。未实现的功能在 UI 中应明确显示“开发中”，不能用假数据欺骗用户。

### 00.3 项目为什么值得研究、值得开发

- **生物计算**：研究组织边界、局部迁移或创面闭合随时间变化的过程，使用可测量的真实生物影像。
- **经典 AI / 深度学习**：CNN、递推状态更新、时序预测、正则化、长期滚动预测、优化和可解释性；不依赖商业大模型 API。
- **可能的科研贡献**：探索在较小真实数据条件下，结合观测状态的局部神经更新规则是否具有更好的长期稳定性；研究可预算约束下模型内控制。**这只是研究假设，不是宣称已经发表级创新。**
- **软件工程价值**：真实的全栈分层架构、稳定接口、自动化测试、可复现实验、数据溯源、优秀 UI 和规范 GitHub 历史。
- **保研/夏令营价值**：可让审阅者看代码、读实验、运行项目、追踪开发决策与 Git 提交，而不只是一张截图。

### 00.4 本项目中几个容易混淆的概念

| 术语 | 在本项目中的准确意思 | 禁止误用 |
|---|---|---|
| **创面/伤口（wound）** | 显微实验中组织或细胞层出现的局部缺口 | 不等于人体临床皮肤伤口 |
| **真实观测** | 从有来源标识的生物实验中取得的原始图像/注释 | 不得用算法生成图冒充 |
| **真实标注** | 发布者提供或人工核实的真实分割标签 | 不得把预测掩膜叫 ground truth |
| **NCA 网格单元** | 局部空间状态计算单元 | 不等于显微镜里的一颗真实细胞 |
| **模型预测** | 训练模型根据前序数据推出的后续状态 | 不等于实际观察到的后续帧 |
| **虚拟干预** | 在数学模型中改变抽象局部场并进行 what-if 计算 | 不等于真实药物、基因敲除、治疗方案的因果效果 |
| **演示数据** | 生成的合成样例或经授权的真实样本 | 合成必须显式标记 `SYNTHETIC` |
| **创新点** | 我们提出、实现并实证比较的具体研究设计 | 不得把“用了 PyTorch / 做了 UI”算创新 |

---

## 01｜最高优先级指令（P0，不可违反）

1. **忠实履行项目愿景，拒绝假实现**。研究、数据、界面中所有“完成”“性能提升”“已训练”等字样必须对应证据。没有模型时只能显示明确标记的合成样例或“尚未训练”。不要编造论文实验数值。
2. **真实数据是硬条件**。必须先检查公开下载和内部文件结构，不能只有一个文献链接就声称“数据集已准备好”。不能要求用户自己做湿实验、向导师要数据或购买私有数据库。
3. **每个 Git commit 必须立即推送 GitHub**。先进行 GitHub 身份验证及远端创建；每个有意义的独立改动都用一条真实 commit 记录并立即 push。推送失败视为流程阻断，先修复同步，再继续新的 commit。不得伪造、回填或改写开发历史。
4. **README 必须与工程同步生长**。第一笔 commit 就要有准确、体面的 README。后续在数据、模型、UI 和结果落地时不断补真实图片及复现信息。绝不能直到项目结束才写一篇华丽但空洞的 README。
5. **前端必须有高级产品设计水准**。不要做“典型 AI 生成网站”；不要用一屏渐变标题、十几张相同圆角卡片、发光装饰、假指标或套模板形成视觉完成度。先设计交互和布局，再实现组件，做真实截图检查并反复调整。
6. **当前先不追求现场演示**。短视频、4 分钟讲解、一键课堂演示、复杂动画效果全部后置；先做好数据、模型、软件工程和 UI 基础。不要为了看上去有成果而抢先做一堆无后台页面。
7. **可复现优先于高分**。研究结论必须有 Baseline、合理拆分、固定 seed、配置、日志、误差分析；如果模型不如传统方法，要记录负结果，而非隐藏。
8. **人类做决策，Codex 负责执行**。日常依本文独立推进；仅在公共 GitHub 身份/权限阻断、数据真的无法取得、研究对象需根本改变、法律许可不明或会影响研究方向的重大选择时，向用户报告并给出可执行方案。
9. **把研究和软件分开治理**。科研结论不因界面动画更漂亮而更可信；UI 中必须分别标识 `OBSERVED` / `ANNOTATION` / `PREDICTION` / `SYNTHETIC` / `IN_SILICO`。
10. **不要泄露秘密**。不得提交 Token、个人目录、`.env`、数据集原始大文件、无发布权影像、生产凭据、系统信息；禁止用 Git LFS 作为绕过版权或隐私限制的方式。

---

## 02｜产品范围与优先级

### 02.1 用户与目的

**主要用户**：本科 AI 研究者（训练、验证、解释模型）；生物计算教师（理解问题和研究方法）；GitHub 读者与夏令营面试官（检查独立工作、复现过程）。

**核心任务**：数据浏览 → 预处理 → 观测窗口选择 → 时序预测 → 真值对照与误差分析 → 研究结果与模型追溯。可交互虚拟干预为下一阶段进阶目标，不影响第一版真实预测链的科学完整性。

### 02.2 功能分级

| 等级 | 功能 | 解释 |
|---|---|---|
| P0 | 数据审计与注册表 | 公开下载、授权检查、逐帧/掩膜/时间间隔验证 |
| P0 | 可重复运行的实验 CLI | 基线、模型训练、评估、输出标准化报告 |
| P0 | 高品质前端设计系统和真实数据浏览器 | 不是占位 Dashboard；至少一条真实时序可浏览 |
| P0 | README、架构文档、真实 GitHub 提交历史 | 从立项起维护 |
| P1 | 经典动力学基线 + NCA 时序预测 | 同样输入/拆分/指标下做比较 |
| P1 | 可视化误差对比与研究报告 | 表格、曲线、误差覆盖图、失败案例 |
| P1 | 本地 FastAPI 应用与后端作业系统 | 让前端以真实 API 访问计算结果 |
| P2 | 约束 NCA 消融、稳定性实验 | 深入研究，严谨记录 |
| P2 | 虚拟干预、A/B 情景比较 | 只在已经稳定的预测模型上建设 |
| P3 | 完整现场演示脚本与视频 | 项目接近完成后做，不排在前面 |
| 不做 | 医疗诊断、LLM 问答、商业云服务、用户登录、3D、多租户 | 与本项目无关，增加不必要复杂度 |

### 02.3 初步可测成功标准

- 从全新克隆的仓库可读懂项目、安装依赖、运行**至少一种无 GPU 的最小验证命令**。
- 数据工具能正确识别至少一组真实动态影像（分辨率、时间顺序、实验分组、图像与标注是否匹配），并给出结构化质量报告。
- 至少有 persistence、经典形态动力学、一个可学习时序模型与基础 NCA 的公平对照（最终纳入哪些对照以数据审计后 ADR 为准）。
- 研究脚本输出真实实验级划分后的指标及失败案例；不要求一定超越全部 Baseline。
- Web 产品主界面使用真实数据及真实状态，具有一致的设计系统、可用性、异常处理和基础无障碍能力。
- README 有**真实软件截图**、产品截图说明、技术架构图、数据来源、复现实验命令、局限与引用。
- GitHub 提交历史与任务/决策相对应，每一个本地提交都能在远端查到，不是一个“Initial commit 上传所有代码”。

---

## 03｜公开数据：从本章开始，不得跳过

> **重要修正**：不要只依赖最初提议的 GigaDB 100118。更适合本科项目直接起步的是公开列出数据压缩包的 Zenodo 7660424。两者是**不同实验体系**，不能在科学报告中当成同一类实验数据简单混训或共享结论。请先完成 M0 数据审计，再决定主研究域。

### 03.1 数据源 A：首选真实动态数据（必须优先核验）

**名称**：Videos of Embryonic Wound Healing in Drosophila and Wound Segmentation  
**发布者**：Backova 等，2023  
**入口**：https://zenodo.org/records/7660424  
**DOI**：https://doi.org/10.5281/zenodo.7660424  
**当前页面事实**：页面标识 Open，公开列出约 **198.7 MB** 的 `Dataset.zip`，描述含 **61 条**果蝇胚胎激光创面愈合视频，原研究有 44/12/5 的 train/validation/test 划分；附 wound segmentation 相关内容。页面记录的帧约每分钟一次，平均序列约 120 帧。**这些是网页元数据，不等于 Codex 已完成下载解析。**  
**生物语义**：**in vivo 果蝇胚胎激光创面闭合**；不是体外 cell scratch assay。  
**授权**：Zenodo 可访问不自动等于可再分发；授权要从记录元数据/附件 LICENSE/作者说明核验，若不清楚只发布源链接、代码和你自己生成的无版权风险示意。

**Codex 必做**：

1. 检查 Zenodo 元数据 API 和实际 `Dataset.zip` 文件下载（支持浏览器/官方直链，无需私有账号）；记录请求结果及下载耗时、体积、校验和。
2. 阅读压缩包内目录结构，列出每条序列、帧数、帧间隔、影像通道、分割标注文件类型与一一对应关系。
3. 重点确认“skeletonized segmentations”究竟是骨架线、边界线还是可转换的完整二值 mask；**不能未经检查就把它们作为 IoU 的真值 mask**。
4. 检查是否能保留官方划分；若存在已发布 train/val/test，优先按其分组，不改变以美化结果。
5. 选取两条短序列构建本地 `sample` 数据集，保留 hash 和源 ID，做可视预览与对齐检查。真实图像若授权不明确则 sample 仅本地存放，README 截图暂用自生成结构图。
6. 记录未知元数据（物理标尺、干预条件等），**未知写 `null`，不推测单位**。

### 03.2 数据源 B：体外划痕实验的独立扩展（需要单独核验）

**名称**：Live time-lapse dataset of in vitro wound healing experiments  
**入口**：https://gigadb.org/dataset/100118 ，DOI https://doi.org/10.5524/100118  
**页面事实**：包含 **31 组**体外伤口/划痕愈合延时实验、两种细胞系、多种条件；页面链接原始数据在 `The Cell: an Image Library` 的不同 group（MDCK 与 DA3）。  
**主要风险**：页面公开的是数据记录与关联入口，原始图像的真实逐帧下载路径、镜像可用性及分组规范需要亲自测试。**不能将 GigaDB 页面存在当成原始数据已下载成功。**

**采用规则**：如果 A 已经可用，先完整做 A；B 可作为**另一个数据域的外部泛化/迁移实验**，或后期独立研究支线。若 B 获得更多高质量数据可提出 ADR 调整主研究域。**不同生物体系不得把同一组数值指标混成单一排行榜。**

### 03.3 数据源 C：明确静态、不能当视频的辅助资源

**名称**：BBBC019v2 Collective cell migration  
**入口**：https://bbbc.broadinstitute.org/BBBC019  
**页面事实**：171 张图像、配套 ROI/ground-truth 描述；以多个 ZIP 形式提供，页面明确为 CC BY 3.0。  
**可用用途**：静态创面/细胞区域掩膜处理、图像预处理鲁棒性测试、静态可视化范例。  
**禁止用途**：不能强行排列成时间序列，不能构造伪造的真实 `t+1` GT，不能把各个视野当同一场景的连续帧。

### 03.4 明确排除的“看起来公开其实拿不到”的资源

2026 年 Zenodo **Wound Healing Assay Time-Lapse Series**，https://zenodo.org/records/21031330，页面标注 **Restricted**，声明需要机构邮件申请和数据转移协议。**不能将它计入免费、无需申请的有效数据来源；不得要求用户去申请它才能开工。**

### 03.5 数据策略：先证据，后算法

- A 若完整下载、可正确解析，优先选择 A 做 NCA 时序预测；先判断是否存在逐帧可靠 mask 或可重建的目标（可改为边界/骨架/面积预测，**前提是明确转化定义**）。
- A 如果下载成功但标签仅适合轮廓/骨架，而不适合完整占据掩膜：重新定义相应监督信号并写 ADR，禁止机械套用 IoU。
- A 如果无法完整下载：调查是否为短期网络/文件服务故障，重试并记录；再审计 B 的真实逐帧数据。两者都不可用时立即报告**研究阻断**，先继续独立的工程骨架、单元测试和合成数值模型，不得改写真实数据目标。
- 小样本按**实验序列分组**；严禁同一个视频不同帧跨训练/验证/测试；如果官方提供固定测试集，必须保留。
- 数据异常、重复帧、缺帧、错误注册、丢失标注或标注含义不明确，都必须被检测并写入审计报告。

### 03.6 数据注册表与最小 Schema

必须落地 `datasets/registry.yaml` 与 `docs/research/data-audit.md`，记录字段：

```yaml
id: drosophila_wound_zenodo_7660424
provider: zenodo
record_url: https://zenodo.org/records/7660424
doi: 10.5281/zenodo.7660424
biology_domain: drosophila_embryo_in_vivo_laser_wound
access_status: to_be_verified
license: unknown_until_verified
redistribution_allowed: false  # 保守默认，直到有明确授权证据
modality: time_lapse_microscopy
is_dynamic: true
annotation_type: to_be_inspected
original_split: to_be_verified
citation: Backova et al. (2023), DOI 10.5281/zenodo.7660424
sample_hashes: {}
verified_at_utc: null
notes: '网页列出公开压缩包；需实际下载、列目录、检查标签定义'
```

统一时序记录的数据契约（Python Pydantic model，序列和帧分开建模）：

```json
{
  "sequence_id": "external-source-unique-id",
  "experiment_id": "biologically-independent-unit-id",
  "dataset_id": "drosophila_wound_zenodo_7660424",
  "biology_domain": "drosophila_embryo_in_vivo_laser_wound",
  "split": "train",
  "frames": [
    {
      "frame_index": 0,
      "timestamp_min": 0.0,
      "image_relpath": "...",
      "annotation_relpath": "...",
      "annotation_type": "UNKNOWN_OR_EXPLICIT_ENUM",
      "height": 128,
      "width": 128,
      "pixel_size_um": null,
      "provenance": "REAL_OBSERVED"
    }
  ]
}
```

图像像素大小、时间戳等示例值仅为**Schema 示例**，不得复制为数据集“已验证真实属性”。落地代码对不满足时间顺序、文件不存在、维度不一致、未知注释类型、跨组泄漏必须报错。

### 03.7 M0 数据验收闸门（严格）

- [ ] 能从公开页面/链接无申请获得至少一个真实视频压缩包；下载命令可复现。
- [ ] 能成功读取不少于 **2 条**有意义的连续序列，每条不少于 **6** 个不同时间点，并检测连续性。
- [ ] 有实际帧内容可视化与至少一个标注叠加的 QA 图；标签不可解析则单独报告。
- [ ] 保存文件哈希、序列清单、来源 URL、标注语义、拆分依据及使用限制。
- [ ] 按原始科学对象准确命名，不将果蝇胚胎称成体外细胞划痕。
- [ ] 在 `docs/research/data-audit.md` 区分：**网页证据 / 已下载核验 / 未解决限制**。
- [ ] 不向 GitHub 推送原始大型影像或许可证不明确的派生图片。

---

## 04｜科学问题和模型：Codex 要实现的真正算法

### 04.1 研究问题（默认 RQ）

> 给定某一真实创面闭合过程的前 `L` 个观测时间点，能否利用具有**局部共享更新规则**的神经细胞自动机，预测接下来 `H` 个时间点的空间形态变化，并在长期滚动预测中保持稳定、可解释、可比较？

**先预测，再干预。** 不可先做一个虚拟画笔，就假设模型具有真实可控制的生物含义。

### 04.2 拟尝试的技术贡献（不能直接在 README 写“首创”）

1. **观测条件化局部状态初始化与更新**：将前 L 帧变换为占据/边界/潜变量状态，学习局部更新规则，而非只拟合最终图案。
2. **长期稳定性约束**：综合多时间步损失、边界平滑或状态约束、递推误差控制，研究是否能够改善远期预测。
3. **模型内可干预动态分析**：在约束预算下改变局部虚拟场，分析扰动敏感性和目标函数优化；只有模型内效果，不能声称现实生物因果有效。

独立性须通过 `docs/research/related-work.md` 的相邻工作矩阵论证；若已有同等方法，进一步收窄更具体的假设，不能照搬论文代码声称自主研发。

### 04.3 模型数学约定

使用二维状态网格：

```text
S_t ∈ R^{B × C × H × W}
P_t = Perception(S_t)            # 局部 3x3/多尺度卷积感知
ΔS_t = f_θ([S_t, P_t, c_t, u_t])  # 共享小型卷积网络
S_(t+1) = Stabilize(S_t + ΔS_t)   # 状态范围/稳定化，可做消融
Y_t = Decode(S_t)                # 预测边界、掩膜或面积相关信号
```

- `c_t` 为合法、有记录的观测条件，缺失则不补造。
- `u_t` 为明确标注的 **VIRTUAL** 干预场；正常真实数据预测时取 0。
- 必须在数据审计完成后决定 `Y_t` 的标签形态，例如二值区域、边界距离图、骨架还是标量面积。这个决定属于 ADR，且影响损失/指标/可视化，不可随意替换。
- 可采用 NCA 共享卷积规则、随机更新或显式边界条件，但应从原理自己实现，并注明参考文献，不可直接把某个现成 repo 作为整项目主体。
- 研究对照的计算预算、训练数据划分、预测 horizon、输入窗口必须一致，不能为 Proposed 设置特权。

### 04.4 Baseline 和最小实验矩阵

至少准备以下层级；部分需要按数据注释实际格式调整，不能为了凑四个模型引入没有意义的对照。

| 对照 | 实现 | 要回答的问题 |
|---|---|---|
| B0 Persistence | 最后一帧复制到未来 | 不预测变化的下限有多好 |
| B1 Classical | 边界前沿匀速演化、形态学/扩散类方法，参数只在验证集调 | 简单机制模型有多强 |
| B2 CNN-RNN | 小型 ConvGRU / ConvLSTM 时序预测 | 通用深度学习是否已足够 |
| B3 Vanilla NCA | 基本局部更新规则，无额外稳定性模块 | NCA 本身能否工作 |
| Proposed | 观测条件化 + 约束/一致性模块（具体以 ADR 确认） | 我们的改动是否带来实证收益 |

**至少需要**：

- 短期/中期/长期 horizon 的预测误差。
- 不同初始观测长度的效果。
- 去掉长期损失、去掉稳定性约束等消融（实际实现模块为准）。
- 由原始实验单位定义的分组测试，而不是随机按图片拆分。
- 3 个不同随机种子（可用低计算量配置），均值和离散程度；算力不足则记录实际次数和局限。
- 失败案例与极端情况：破损标签、闭合程度突变、长时序不稳定、域偏移。

**指标选择必须匹配标签语义**：如果是真实二值 mask，可以评估 Dice/IoU、边界距离、面积 MAE；如果只有 skeleton/boundary，优先用中心线/边界距离、Hausdorff95 和几何指标；如果只能可靠提取面积，则使用时间曲线 MAE 与面积变化误差，**不允许造 mask 来计算貌似漂亮的 Dice**。全部明确物理单位是否已知。

### 04.5 划分与实验可信度

- 训练/验证/测试按**完整序列/独立实验**分组，同序列不同帧与其派生裁剪块不得跨 split。
- 原始官方拆分优先；不能为了追分改动 test。
- 数据预处理统计量只能用 train 拟合，然后应用到 val/test。
- 从前 L 帧预测未来 H 帧时，模型输入和归一化不许利用未来 GT。
- 同一个数据的伪标签不能既作为训练监督又充当独立真值而不标注。
- 重复帧 hash/近重复检验和 group leakage test 写进自动化测试。
- 训练日志记录完整参数、seed、git SHA、数据 manifest hash、模型 ckpt hash、依赖锁定版本。

### 04.6 训练与资源策略

- 本科规模：先运行 `64x64 / 128x128` 网格、小批量、小模型、有限 horizon，证实训练流程、指标和数值稳定性，再扩大。
- PyTorch 必须 CPU 可运行；检测 CUDA 则可加速。不要强制要求昂贵 GPU 或云训练。
- 优先 fp32 正确性、梯度裁剪、早停、checkpoint resume；混合精度作为可选优化。
- 大模型不在 Git：模型权重本地缓存；公开小权重需先确认使用条款和 GitHub 文件限制，可使用 Release 附件、明确哈希和来源。
- 对数值崩溃（NaN、Inf、全空区域）、张量尺寸、GPU/CPU 一致性给出测试。

### 04.7 虚拟干预（后期独立模块）

当真实时序预测已经通过验收后，才能新增：

- `u_t(x,y)`：局部正/负影响抽象场，以**模型计算参数**解释，绝不直接映射药物剂量。
- 约束预算 `Σ|u| <= B`，目标 `loss_to_target + λ × intervention_cost + γ × spatial_roughness`。
- 最少随机干预与一种可优化策略进行比较；可设置固定 seed 比较 A/B。
- 页面醒目写 `IN-SILICO / 模型内虚拟实验`，实验结果不支持现实治疗或生物因果结论。

---

## 05｜软件总体架构（单仓库，清楚分层，不要过度设计）

### 05.1 技术栈（默认；发生变更须 ADR）

| 子系统 | 选型 | 理由 |
|---|---|---|
| 前端 | React + TypeScript strict + Vite | 组件化、强类型、迭代快 |
| 样式 | Tailwind CSS + 自定义 design tokens + Radix/shadcn 可访问基础组件 | 用底层能力打造独特视觉，而不是直接套出千篇一律的卡片界面 |
| 状态 | TanStack Query（服务端状态）+ Zustand（轻量本地实验会话） | 数据与交互边界清楚 |
| 可视化 | Canvas 2D / SVG；数据曲线 ECharts（按需） | 适合图像叠加、轮廓、时间轴 |
| 后端 | Python 3.12+，FastAPI，Pydantic v2，SQLite + SQLAlchemy | 轻量、可本机独立部署 |
| 计算 | PyTorch，NumPy，SciPy，OpenCV / scikit-image | 深度学习和图像处理基本组件 |
| 任务执行 | 本地持久任务队列 + 独立 worker 进程 | 避免长时间推理堵塞 API；不急于 Redis/K8s |
| 包管理 | `uv` + `pnpm` + 锁文件 | 可重复安装 |
| 质量 | pytest、ruff、mypy（重点模块）、Vitest、ESLint、tsc、Playwright（后期） | 分层测试 |
| 文档与版本 | Markdown、Mermaid、Git、GitHub Actions、ADR | 便于 GitHub 阅读和长期维护 |

优先满足 **Windows 11 + PowerShell / VS Code + Git Bash**，兼容 Linux/WSL。不要求 Docker 才能开发；后期可以提供 Compose 作为可选方案。Python 模块布局、uv 工作区配置根据实际可运行性决定，不要机械复制导致导入报错。

### 05.2 单仓库目标目录

```text
morpholab/
├── README.md                         # 中文为主，图文并茂，逐阶段维护
├── README.en.md                      # 精简但准确的英文介绍，后期完善
├── AGENTS.md                         # Codex 可操作规范：与本总任务书一致
├── LICENSE                           # 经选择并核实的源码许可证
├── CITATION.cff
├── CONTRIBUTING.md
├── CHANGELOG.md
├── .editorconfig
├── .gitignore
├── .env.example                     # 不得包含秘密
├── .github/
│   ├── workflows/ci.yml
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── docs/
│   ├── project/vision.md
│   ├── project/requirements.md
│   ├── project/roadmap.md
│   ├── project/decisions/ADR-0001-*.md
│   ├── research/data-audit.md
│   ├── research/related-work.md
│   ├── research/hypotheses.md
│   ├── research/experiment-protocol.md
│   ├── research/results.md
│   ├── research/limitations.md
│   ├── architecture/system.md
│   ├── architecture/api.md
│   ├── design/visual-language.md
│   ├── design/component-inventory.md
│   ├── development/git-workflow.md
│   └── releases/
├── assets/
│   ├── brand/                        # 自制 logo、标识、图标（允许提交）
│   ├── diagrams/                     # 自己生成的架构图/流程图
│   └── screenshots/                  # 真实运行截图，审核版权后提交
├── datasets/
│   ├── registry.yaml
│   └── README.md
├── frontend/
│   ├── src/{app,pages,features,components,lib,styles,store,api}/
│   ├── public/
│   ├── tests/
│   └── package.json
├── backend/
│   ├── app/{api,core,db,schemas,services,workers}/
│   ├── tests/
│   └── pyproject.toml
├── ml/
│   ├── morpholab_ml/{data,models,baselines,training,evaluation,inference,control}/
│   ├── configs/
│   ├── tests/
│   └── pyproject.toml
├── scripts/
│   ├── audit_data.py
│   ├── prepare_data.py
│   ├── train.py
│   ├── evaluate.py
│   ├── report.py
│   └── verify_remote.py
├── tests/fixtures/                  # 极小合成 fixture，可公开
└── artifacts/                       # .gitignore；原始影像、大日志、大权重
```

该树是**最终演化方向**，不是要求首个 commit 就创建几十个空目录和占位文件。**按需创建真实有用途的目录、文件与测试；不制造空壳。**

### 05.3 真实的数据流

```mermaid
flowchart LR
  SRC[公开数据来源] --> AUD[审计与校验]
  AUD --> PRE[预处理与分组]
  PRE --> DSET[版本化数据清单]
  DSET --> EXP[基线 / NCA 训练评估]
  EXP --> ART[模型与真实实验产物]
  ART --> API[FastAPI + 后台 Worker]
  API --> UI[React MorphoLab 工作台]
  UI --> API
  UI --> DOC[截图 / 报告 / README]
```

关键边界：

- `ml/` 是纯 Python 包，不 import HTTP/React/数据库；给定路径/张量/配置应能离线训练或预测。
- `backend/` 不在路由函数中执行大型训练循环；重任务通过 worker 执行，有 job 状态和结果目录。
- `frontend/` 通过 OpenAPI 类型与 API 通信，不能重复实现科学指标算法。
- 原始数据、预处理数据、模型权重、实验日志均有**元数据和 hash**；从公开仓库运行脚本可产生新产物，但不会提交 GB 文件。
- 早期若后端尚未完成，UI 可使用**清楚标识的本地合成 fixture**开发组件；绝不让此状态在 README 中冒充真实研究功能。

### 05.4 最小 API 合同（等真实数据通路完成后分步实现）

```text
GET    /api/v1/health
GET    /api/v1/datasets
GET    /api/v1/datasets/{id}
GET    /api/v1/sequences?dataset_id=...
GET    /api/v1/sequences/{id}
GET    /api/v1/sequences/{id}/frames/{frame_index}
POST   /api/v1/experiments/predict
GET    /api/v1/jobs/{job_id}
POST   /api/v1/jobs/{job_id}/cancel
GET    /api/v1/jobs/{job_id}/result
GET    /api/v1/experiments
GET    /api/v1/experiments/{id}
POST   /api/v1/scenarios                  # P2, 模型内虚拟干预
```

- 所有 POST 的 schema 必须声明数值边界，拒绝无效路径/过大输入/非法 frame 数。
- 响应统一包含 `schema_version`、`provenance`、`dataset_id`、`model_id`、`run_id`（可为空但不可凭空填）、`created_at_utc`。
- `provenance` 枚举：`REAL_OBSERVED`, `HUMAN_ANNOTATION`, `MODEL_PREDICTION`, `SYNTHETIC`, `IN_SILICO`；前端以醒目标识区别。
- 返回图像使用分离的可缓存图像资产接口而不是将所有像素塞进 JSON。
- 标准错误：`code, message, details, trace_id`；生产状态不回传本机绝对路径、堆栈、凭据。
- 每个 job：`queued, running, succeeded, failed, cancelled`，明确保存状态和失败理由，重启恢复一致。

### 05.5 配置 / 可复现约束

- 统一配置使用 YAML/类型化结构，不能在十几个 Python 脚本复制常量。
- 数据预处理配置包含输入版本、尺寸、插值方法、时间间隔处理、归一化统计来源、标签类型。
- 每条实验保存 `run_id`, `git_sha`, `source_manifest_sha256`, `seed`, `model_config`, `train_config`, `metrics`, `environment`。
- CUDA 不可用时不能直接报一个难懂的导入错，应退化 CPU 或给出明确提示。
- 仅有网络离线需求时，`pytest`/linter/基本 UI 与小型纯合成计算需正常执行。

---

## 06｜设计规范：前端必须好看、高级、但不要 AI 模板味

> **注意：这里描述的是软件美术指导，不是让你生成几张漂亮效果图就算完成。最终验收对象是浏览器实际运行页面。**

### 06.1 整体设计定位

产品气质关键词：**Research Instrument / Editorial Precision / Quiet Confidence / Computational Biology**。中文可理解为“带编辑设计感的专业科研仪器”。参考成熟研究工具对信息密度、状态控制与细节的重视，但**不直接抄袭任何特定产品的布局、图标或品牌**。

希望看到的效果：像一款由认真设计师和科研工程师合作完成的软件，而不是使用通用 UI 组件让 AI 一口气生成的后台管理模板。

**明确拒绝**：

- 大面积紫蓝粉渐变、赛博荧光、毫无意义的粒子背景、巨大机器人/大脑插画。
- 首页“一句空洞标语 + 四张 AI 通用功能卡 + 一排假增长曲线”。
- 所有容器都使用同一圆角、同一阴影、同一填充色，视觉层级模糊。
- 大段虚词营销文案：“赋能生物未来”“探索无限可能”“AI 重塑科研”。
- 一口气安装多个巨大组件库导致不同按钮、表格、对话框风格互相冲突。
- 给不存在的功能设计可点击按钮，点进去却什么也不做；生成精美但不真实的数据图。
- 截图使用未经授权的生物论文插图、图库图片或“示意真实实验”的 AI 生图。

### 06.2 设计方法：先做信息架构和图形语言，再写页面

Codex 必须先交付 `docs/design/visual-language.md`：包含页面主次关系、设计关键词、色板、字阶、空间单位、圆角与线条、交互状态、图像标注规范。先做三个关键区域的静态可点击布局，做浏览器截图审视，再接模型和复杂图表。

使用的默认视觉方向（允许经过实际浏览器观察做小幅微调）：

| Token | 建议值 | 用途 |
|---|---|---|
| `--bg` | `#0B1014` | 主深色背景，避免纯黑死板 |
| `--surface` | `#121A1F` | 工具面板 |
| `--surface-raised` | `#1A252B` | 选中或悬浮面板 |
| `--border` | `#2A3941` | 细分割线 |
| `--text-primary` | `#E7F0EE` | 主信息 |
| `--text-secondary` | `#91A5A8` | 次信息 |
| `--accent` | `#8EC5B5` | 观察和有效交互 |
| `--forecast` | `#E2B875` | 模型预测轨迹 |
| `--intervention` | `#D79583` | 虚拟干预场 |
| `--uncertainty` | `#93A5CE` | 不确定度 / 多模型差异 |

**原则**：大多数区域使用低饱和度冷灰，颜色只服务状态；同一视图中预测与真值必须通过**颜色 + 线型 + 文本**多重区分。浅色主题可后置，不应为做两个粗糙主题牺牲一个精致主题。

排版：有节制的字体层级；中文 UI 推荐系统可靠字体栈，不下载或提交无授权字体文件；英文字母、序列名、实验编号可用简洁的等宽/数字字形；支持中英文混排，数字表格右对齐。文字短而信息明确：例如“未来 12 帧”“按实验分组”“边界误差”，而非宣传文案。

### 06.3 空间结构：围绕科学画布，而不是围绕卡片

**主要展示断点**：1440×900；最小可用桌面：1280×720。后续兼容移动端至少能阅读项目、查看实验元信息，复杂实验操作明确要求桌面宽度；不要在手机屏上硬塞三个栏目。

目标工作台草图：

```text
┌─ MorphoLab ─────────────────────── Dataset / Experiment / Docs ───────────────┐
│  STUDIO  /  生物体系  /  实验序列 ID                  数据来源状态与模型版本    │
├─────────────┬───────────────────────────────────────────┬────────────────────┤
│  数据与操作  │                                           │  观测/预测元信息      │
│             │         主显微图像 / 边界画布              │  指标                │
│  序列选择   │       （图像缩放、对齐、叠加）             │  误差与单位          │
│  时间窗口   │                                           │  数据质量            │
│  视图层级   │                                           │  模型状态            │
│             ├───────────────────────────────────────────┤                    │
│             │  时间轴  ────────────────── 观测 | 未来    │                    │
├─────────────┴───────────────────────────────────────────┴────────────────────┤
│  状态栏：OBSERVED / PREDICTION   运行设备   实验划分   数据许可   Git SHA       │
└──────────────────────────────────────────────────────────────────────────────┘
```

中间图像区域永远是最重要的信息；侧栏可以折叠，时间轴和数据来源状态可一直看到。教学展示时内容一眼可懂，科研使用时经得住反复切换。信息不足的阶段不摆占位数字，显示明确空状态及下一步操作。

### 06.4 页面优先级与真实交互

1. **`/` Overview**：不是营销官网，而是精致、简洁的项目入口。包含一句准确介绍、真实进度状态、数据样本入口、最新可运行功能、研究问题卡片（不要通用营销式四宫格）、README/GitHub 链接。
2. **`/datasets` Dataset Archive**：主数据源概览、获取状态、来源 DOI、生物语义、序列数量、分组、授权标签、下载及校验状态；真实可筛选和查看。
3. **`/studio/:sequenceId` Morphodynamics Studio**：主画布、原始帧/标签/预测层切换、时间轴、缩放、基本帧步进、观测窗口边界；后续才加入 rollout、模型比较与控制画笔。
4. **`/research` Research Notebook**：基线结果、曲线、配置、随机种子、失败案例、实验日志和统计表；没有实验结果时展示“尚未跑出结果”而不是假指标。
5. **`/methods` Methods & Evidence**：本项目用何种局部规则、和已有研究区别在哪里、数据局限以及论文引用。

**界面交互清单**（从少到多实现）：时间轴拖动与单步、图像层切换、原图/标签对齐、放大缩小、鼠标读数、数据源切换、相邻帧对比、运行状态反馈、训练结果筛选、加载模型与错误提示。每个可见控制至少有键盘焦点、hover、disabled、loading、error 和必要 aria 信息。

### 06.5 动效与渲染底线

- 动效用于**解释状态过渡**：帧切换、边界层进出、拖拽定位、播放/暂停；每个动效有明确意义，尊重 reduced motion。
- 图像叠加使用 Canvas（必要时使用 OffscreenCanvas/worker，但不要过早优化）；控制帧缓存，避免播放时内存飙升。
- 使用比例尺和时间标签；没有物理单位时写 `pixel` 或 `frame`，不捏造 `µm`、`minute`。
- 对预测层用透明填充或虚线轮廓；原始图像要保持可辨；不要将不同来源的数据配色糊成绚丽色块。
- 任何图表需有可解释轴、数据数量 n、模型标识、样本集划分、指标含义；没有 n 不做性能结论。
- 无障碍：键盘可操作、必要对比度、文本与颜色共同区分状态、重要信息可读。

### 06.6 前端实际验收（不能只写审美自评）

- [ ] 对 1440×900 和 1280×720 的实际浏览器截图进行设计审查，无遮挡、溢出、布局抖动。
- [ ] 页面有主次关系、节奏、留白和有效信息密度；**不依赖大量卡片和阴影**。
- [ ] 字体/数字/图例/线型协调；错误/空状态经过设计；没有无效按钮。
- [ ] 逐页走查的设计 review 记录在 `docs/design/reviews/`（截图可提交但必须真实、无敏感内容）。
- [ ] 核心页面自动化 E2E 走通后再声明其功能“可用”。
- [ ] 至少邀请负责人检视关键视觉风格的截图；常规小修 Codex 可自行进行。

---

## 07｜GitHub README：这是产品门面，不是最后一天的宣传海报

### 07.1 README 的角色

审阅者打开 GitHub 的 **5 秒内**应知道：MorphoLab 是什么、研究哪类真实生物数据、用了什么传统 AI 方法、现在哪些东西真的能跑。往下滑能看到真实界面、技术图解、可复现实验和开发记录。这种品质主要靠内容可信、排版克制、图片真实，而不是大量徽章和表情符号。

**README 用中文为主，附英文概述并提供 `README.en.md`；全文尽量像认真研究者自己写的，不用广告腔。**

### 07.2 README 强制信息结构（随着项目进度逐步填满）

1. **顶部品牌区**：自主设计的低调 Logo/字标 `MorphoLab` + 清楚、副标题式一句话定义；一个 GitHub 仓库内真实的产品截图（当软件实际可运行后加入）。
2. **项目现状**：`Research prototype / Work in progress` 等真实阶段标签；哪些已实现、哪些仍在开发，用简洁文字说明。不加假 `Build passing` 徽章。
3. **Why / The Question**：两三段解释研究动机、真实生物场景和为什么需要局部时序建模。准确区分体内和体外。
4. **What it does**：用 3–5 个**实际已实现**功能块说明产品能力；每项有真实截图/图解，不写虚构操作。
5. **Product Tour**：专业排版的截图组；建议数据浏览、时序工作台、预测对比、实验结果四类；只有截图来自真实运行才允许加入。
6. **Method at a glance**：精美但清晰的原创架构图（SVG/Mermaid），说明数据审计 → 预处理 → NCA/对照 → 指标 → Web，不要黑盒大脑图片。
7. **Research Protocol & Evidence**：拆分策略、实验设置、Baseline、主要指标、已有实际结果与局限。没有结果时标 `Pending evaluation`，不能写待验证结果好像结论。
8. **Getting Started**：核验过的工具版本、Windows/PowerShell 和 Linux 启动步骤、测试、样本下载方式，告诉读者哪些命令无需 GPU。
9. **Reproducing Experiments**：公开配置、seed、数据脚本、输出目录、复现命令；注明真实数据可能需要独立下载及许可。
10. **Engineering**：目录概览、测试 CI、架构文档、贡献方式、GitHub 开发历程入口。
11. **Data, Licenses & Credits**：逐项数据 DOI/许可/原始作者，NCA 论文与工具参考；区分算法思想受启发和代码实现自主开发。
12. **Roadmap & Limitations**：当前阶段与尚未解决问题；不要把计划包装成已发布功能。
13. **Citation / Contact**：`CITATION.cff` 与相关资料入口。

### 07.3 图片和排版标准

- 真实截图放 `assets/screenshots/`，统一命名 `overview-v1.webp`, `studio-real-sequence.webp`, `forecast-comparison.webp`, `research-evaluation.webp`；**没实现就没这个文件**。
- 用简洁的 Markdown 图片与标题，必要时少量标准 GitHub 支持的 `<picture>` 来兼容深浅主题；不依赖 GitHub 不支持的复杂 CSS。
- 每张图片要有说明：“哪一条数据、显示的是什么、是否模型输出”。科学图含轴和图例。
- 架构图可自己用 Mermaid / SVG 创建；图表来自真正的实验报告脚本导出，不由视觉生成器伪造。
- Logo 和封面图应自行制作或确认使用权；禁止从 Google 图片搜索结果复制未经授权资源。
- 有意义的图片优先于 30 个勋章。最终 README 插图建议 4–8 张，取决于真实内容，质量比数量重要。
- 所有外链需要检查可访问；相对链接路径和锚点点击应正确。

### 07.4 早期 README 也必须看起来完整、准确

- **第一次 commit**：简洁标题、正确定位、当前状态、准备解决的问题、路线图、引用和“从哪里开始”（哪怕此时只有设计与审计命令）。
- **数据审计之后**：写清数据已验证到哪一级，不把网页介绍当成下载验证。
- **前端初版之后**：加入第一张**真实浏览器截图**，并标明“数据浏览器 UI”“哪些功能尚不可用”。
- **模型结果之后**：更新预测对照/真实指标及运行命令；没有结论时不要编造。
- **发布之前**：截图质量统一、命令从干净克隆通过、英文摘要、引用和许可证完善。

### 07.5 README 文案风格示例（内容风格参考，不得机械复制未实现状态）

**推荐**：“MorphoLab 研究创面边界如何随时间变化。我们尝试用可学习的局部更新规则预测显微影像中后续形态，并用实验级分组评价长期预测误差。”  
**不推荐**：“MorphoLab 是一个革命性的 AI 生物医学平台，重新定义未来科研，实现精准智能创伤修复。”

---

## 08｜Git 和 GitHub：从第一天开始留下一条真正可追踪的开发轨迹

> **本章是硬性操作规程，不是建议。Codex 必须自己完成 Git 初始化、GitHub 创建、真实提交与推送（前提是用户的环境已授权 GitHub）。** 用户要求仓库在 GitHub 上呈现完整从零开发的过程，因此不要只维护本地 Git，也不要最后只做一个“全量上传”提交。

### 08.1 开始编码前先核查 GitHub 环境

先执行并记录结论（禁止打印令牌）：

```bash
git --version
gh --version
gh auth status
git config user.name
git config user.email
```

若未安装 GitHub CLI，优先引导安装官方 `gh`；若未登录，执行 `gh auth login` 并让用户**自行完成安全的交互式授权**。不要索要或读取明文 Token，不要替用户制造账户。`gh auth status` 的敏感字段不应复制进公开文档。检查 Git 作者身份是否配置恰当；若缺失，向用户索取公开 Git 作者名/提交邮箱的授权选择，而不是随机捏造身份。

**公开权限**：这个项目最终要成为可审阅的 GitHub 开源仓库。若用户已明确允许公开创建，则采用 `--public`；创建前检查 `.gitignore`、数据目录、环境文件和许可证。如果 GitHub 凭据不可用，不得声称已经推送；报告阻断并保留当前文件，但**不得继续积累未同步 commit**。

### 08.2 首个 GitHub 仓库创建流程

建议默认使用最简单、最能展示连续成长的 `main` 分支。`morpholab` 仓库由 Codex 从空目录建立，项目负责人可在用户界面或 GitHub 网站上看到它的成长。下面为示例顺序，具体参数需以本机 `gh` 版本为准：

```bash
mkdir morpholab
cd morpholab
git init -b main
# 首先创建真实存在的 README.md、.gitignore、项目规范、规划文档等
git add README.md .gitignore AGENTS.md docs/project/vision.md docs/project/roadmap.md
git diff --cached --check
git commit -m "chore: initialize MorphoLab research project"
gh repo create morpholab --public --source=. --remote=origin --push
# 验证远端仓库与当前分支确已存在，首次提交已推送
git remote -v
git status -sb
git ls-remote origin refs/heads/main
```

**核心约束**：第一条 commit 必须很早发生，内容只是一开始实际完成的项目章程、基本规范、README 和项目结构；不能在一个首提交里突然出现全部算法和前端。

### 08.3 每一条 commit 的同步协议（强制，任何阶段适用）

每完成一个独立、可以解释的工作单元：

1. 确认 `git status`，只选择本次变更的文件；检查是否含凭据、真实影像、大模型权重、临时日志。
2. 执行与改动相称的测试、类型检查、格式化、文档链接检查或 smoke test，记录实际结果。
3. 执行 `git diff --check` 与 `git diff --cached` 检查；**不得 `git add .` 之前不看变更**。
4. `git commit -m "type(scope): meaningful change"`，message 描述做了什么而非“update”。
5. **立刻执行 `git push -u origin HEAD`**（在 main/当前正常开发分支）；不要先进行第二次 commit。
6. 用 `git rev-parse HEAD` 和 `git ls-remote origin refs/heads/<当前分支>` 核对本地/远端 SHA 一致。二者不一致必须阻断后续提交，排查后再继续。
7. 更新阶段工作记录，在阶段报告里列出 commit SHA、GitHub commit URL、测试结果和解决的问题。

下面给出**用于说明的单次变更命令**，不要把具体 commit message 每次照抄：

```bash
# 先运行当前改动相关检查
# 例如：uv run pytest -q 或 pnpm --dir frontend lint

git status --short
git add <本次需要提交的明确路径>
git diff --cached --check
git diff --cached --stat
git commit -m "feat(data): add verified time-lapse manifest parser"
git push -u origin HEAD
# 核验：检查当前分支的 HEAD 是否与 origin 上的分支完全一致
git rev-parse HEAD
git ls-remote origin refs/heads/$(git branch --show-current)
```

PowerShell 中的最后一条可以用 `git ls-remote origin "refs/heads/$(git branch --show-current)"`，避免 shell 兼容错误。也可以将可靠的核验实现为 `scripts/verify_remote.py`，在 Windows、Git Bash、Linux 运行。**每个 commit 后立即推送并验证，而不是仅依赖 `git status` 或 hook 的输出。**

### 08.4 什么样的粒度才像真实开发？

**推荐的连续提交（示例）**：

```text
chore: initialize MorphoLab research project
 docs: define biology domain and dataset audit criteria
 chore(ci): add Python lint and unit-test workflow
 feat(data): implement Zenodo archive manifest validation
 test(data): reject out-of-order and leaked sequences
 feat(frontend): establish typography and layout primitives
 feat(frontend): add validated dataset archive view
 feat(ml): implement persistence forecasting baseline
 feat(ml): add local state update NCA model
 test(ml): cover rollout stability and seed determinism
 research: record baseline results on fixed group split
 fix(frontend): correct time-axis alignment in sequence view
 docs(readme): add real dataset browser screenshots
```

这些只是示范节奏，**绝不允许为了“好看的 Git 历史”在一次性生成代码后回填这些提交**。必须真按过程完成、测试、提交、推送。提交内容小到可以审查，但也不能为了刷 commit 数而把一句话拆成十次没有意义的提交。

### 08.5 分支 / PR / Issue 策略

- 单人开发默认 `main`，每个 commit push，方便读者沿着时间查看从 0 到 1 的开发过程。
- 复杂或风险较高的研究实验可使用 `feature/xxx` 分支，但**每条 feature commit 一样立刻推送**，推荐 PR 记录设计、截图、测试与失败尝试；合并仍需保留可追踪 commits。
- GitHub Issues 用于记录需求、研究假设、缺陷和阶段验收。使用真实、具体标题；建议 labels：`data`, `research`, `frontend`, `backend`, `quality`, `docs`, `blocked`。
- ADR（架构决策记录）采用递增编号 `ADR-0001-...md`，记录**背景 / 备选 / 选择理由 / 后果 / 证据 / 日期**。模型目标和数据语义改变必须有 ADR。
- 发现错误用新 commit 修复；需要撤销已推送内容用新的 `git revert`，**禁止随意 force push、reset 覆盖已公开历史、改已推送 commit 日期/作者、重写美化历史**。
- 未经用户授权，不删除仓库、公开私密数据或切换仓库权限。

### 08.6 同步失败处理（非常重要）

遇到 `git push` 因网络、凭据或 GitHub 冲突失败时：

1. 停止写新的 commit，不继续实现下一模块；可进行只读诊断。
2. 检查 `git remote -v`、`gh auth status`、远端状态和是否存在同名远程分支。
3. 按 Git 正常协作规则处理可快进的更新或明确冲突；**不得使用 force push 掩盖问题**。
4. 恢复后核对 SHA，同步成功后才能继续开发。
5. 若用户需网页登录或环境没有推送权限，简明报告需要的动作；不要索要密码或在公开日志中粘贴 token。
6. 报告里准确写 `local_commit_sha`, `pushed: false`, `reason`，不能说“已同步 GitHub”。

**理想不变量**：在一个独立任务完成并进入下一项之前，`git rev-parse HEAD == git ls-remote origin refs/heads/<branch>`。Git hook 可以辅助，但不替代推送后的核验。

### 08.7 CI 和发布纪律

- 第一阶段建立最小 CI：Markdown/格式检查、Python 核心测试（用轻量 fixture）、前端 lint/build（前端创建后加入）。
- GitHub Actions 不下载数 GB 的真实实验数据，不跑小时级 GPU 训练；发布重型实验通过脚本、本地记录和可复现说明。
- 对公共仓库使用最低需要权限的 `GITHUB_TOKEN`，不要把个人 PAT 写进仓库或 action 日志。
- `v0.x` tag 只在通过明确阶段验收后创建；不能因为第一版 UI 看起来漂亮就标 `v1.0.0`。
- 每条更新 README 中的当前功能状态与实际 tag 一致；`CHANGELOG.md` 不编造发布说明。

---

## 09｜软件安全、可靠性与工程质量

### 09.1 数据与模型安全

- 默认 `127.0.0.1` 单机监听，除非明确选择安全的部署方式。
- 禁止使用用户提交的字符串直接拼接文件系统路径；数据集路径必须在注册表允许的根目录之下。
- 文件上传需限制大小、格式、宽高、帧数、解压后大小与路径穿越；不执行来自数据集的脚本。
- 无权限的第三方数据不得随项目仓库再分发；数据下载脚本应记录来源与 checksum。
- 不将本地绝对路径、用户名、访问令牌、敏感环境变量、堆栈私有信息返回前端。
- 训练模型不应直接使用不受信任的 pickle 文件作为外部上传；权重加载来源受控且校验 hash。

### 09.2 基础质量闸门

**Python**：`ruff check`、`ruff format --check`、`pytest -q`、适当范围 `mypy`。  
**TypeScript**：`tsc --noEmit`、ESLint、Vitest、构建。  
**Web E2E（页面稳定后）**：Playwright 测试数据浏览、图像帧切换、错误和空状态、时间轴、实验结果。  
**依赖和复现**：`uv.lock`、`pnpm-lock.yaml`、测试固定种子、结果元信息。  
**文档**：README 的实际命令验证、图片路径检查、链接抽检、数据来源引用核对。

### 09.3 测试矩阵

| 层级 | 必测情境 | 证明方式 |
|---|---|---|
| 纯单元 | NCA shape/dtype、数值有限、seed、空掩膜、梯度传播 | pytest |
| 数据约束 | 异常时间顺序、重复帧、跨组泄漏、缺失注释、hash 不匹配 | pytest + audit 输出 |
| 训练集成 | 小合成数据 1 epoch、权重保存加载、checkpoint resume | 自动化 smoke |
| 接口 | 类型校验、边界/非法输入、任务失败恢复、下载错误 | FastAPI TestClient |
| 前端组件 | 加载/错误/空状态、时间轴、数据源状态、图像层控制 | Vitest |
| 端到端 | 选择真实序列→逐帧浏览→看来源；模型就绪后加入预测链 | Playwright |
| 非功能 | Windows/Linux 运行、CPU fallback、页面溢出、长任务非阻塞 | 操作记录和性能报告 |

不能只是写了 tests 文件就宣称通过；每个阶段报告实际测试命令与通过/跳过/失败数。无法执行的测试应记录原因和风险。

---

## 10｜分阶段执行顺序（核心：不要一次性做完）

> 本计划只定义**工程依赖顺序**，不是要求 Codex 许诺固定天数完成。每一阶段都要有可检查的真实成果、相称的测试、若干真实 commit，并在每个 commit 后立即 push。**“演示”推后，但“高质量界面设计”和 README 不推后。**

### M-1｜仓库从零启动：项目要先存在于 GitHub

**目的**：让人打开 GitHub 能立即知道这不是一坨 AI 生成代码，而是一个有严肃目标、有开发规划、从第一天公开迭代的项目。

**任务**：

1. 检查环境：Git、GitHub CLI、Python、Node、pnpm、uv；记录缺失和替代方案，不在未获授权时更改全局系统配置。
2. 初始化 Git，建立 `.gitignore`、README、AGENTS.md、项目愿景、开发路线图、基本决策流程。
3. `gh auth status`，创建 GitHub `morpholab` **公开**仓库（若已有同名仓库先验证归属，不能覆盖别人仓库）。
4. 第一条真实 commit 立即 push 并核验 SHA；以后每条都这样做。
5. 建立 `docs/development/git-workflow.md` 与若干核心 Issues（如果 gh 权限和 API 可用），建立初版 CI。
6. README 首版写得准确、美观、克制，至少包含产品定义、研究目标、数据风险、当前状态、路线图与参考来源。

**交付/验收**：公开远端仓库、首个 SHA 和 URL、README 首页、Git 规范、最小 CI。**此阶段不应包含训练模型和华丽假页面。**

### M0｜公开数据与相关工作实测审计（最高研究风险）

**任务**：

1. 调研 Zenodo 7660424、GigaDB 100118、BBBC019 的具体获取、许可证、原始结构和论文关系。
2. 实际下载 A 的公开压缩包并解析少量真实序列；提供 sample 选择逻辑、QA 可视图（本地）、checksum。
3. 明确标签到底是边界、骨架、mask 或其他；若需要加工，给出数学/工程定义和对应 QC。
4. 梳理文献：NCA 原始论文、条件 NCA、时间序列动态预测、伤口闭合边界建模、相关 GUI/数据分析工具；至少做一张对比矩阵，标出“别人已经做了什么 / 本项目要检验什么 / 潜在重复风险”。
5. 形成 `docs/research/data-audit.md`, `related-work.md`, `hypotheses.md`, `datasets/registry.yaml`，并写可运行审计脚本、单元测试。
6. 制定 ADR：主数据域、目标监督信号、分组划分和初始指标；未经数据证据禁止开始正式 NCA 训练。

**验收**：满足 §03.7 的硬条件，并能提供实际运行数据审计日志；数据集许可与再分发判定已记录。阻断时请报告，**不可拿静态图/虚构序列冒充通过**。

### M1｜设计系统与高品质软件骨架（前端从此刻认真做）

**任务**：

1. 写视觉语言文档、页面信息架构、组件规范与状态语义；避免炫技式主页。
2. 创建 React + TypeScript + Vite + Tailwind，建立 tokens、排版、框架布局、侧栏、导航、通用状态组件。
3. 创建 `/`, `/datasets`, `/studio/:sequenceId` 的**真实可运行**页面框架。若有本地真实 sample，则接入真实帧浏览；暂未接入部分显式显示不可用。
4. 数据浏览页能够显示来源 DOI、数据域、时间戳/帧数、验证状态；带原始影像、标签层切换。
5. 做 1440×900 截图审查与适配，提交合理的实际软件截图到 assets；README 增加第一张产品图片并标明已实现范围。
6. 建立前端 component 测试、TS strict、lint、build 与 CI。

**验收**：前端观感达到专业科学软件标准，而非模板 Dashboard；序列切换、图像显示、时间轴、错误与空状态**真实可用**；截图来源确实为运行中的程序。

### M2｜可复现的数据管线和经典 Baseline

**任务**：

1. 将真实动态数据转成可分组、可追溯的统一中间格式；处理时序、比例、对齐及标签语义。
2. 实现不少于 B0 Persistence 与 B1 Classical 的可运行基线；可按数据有效性添加面积/边界直接预测基线。
3. 建立 evaluation runner，可输出 JSON/CSV、按实验分组汇总、失效案例图及指标解释。
4. 加入严格泄漏测试、输入质量检查、指标边界情况测试。
5. 更新 README 的数据使用和 Baseline 命令；用事实描述当前结果。

**验收**：从审计通过的真实数据到 Baseline 指标输出能一条或少量命令复现；失败案例可回溯到序列 ID。

### M3｜自主实现 NCA 与经典深度学习对照

**任务**：

1. 实现基础 NCA、状态编码/解码、训练 loss、rollout、检查点和推理接口；先用极小的纯合成数值 fixture 测试梯度、shape 与稳定性。
2. 将基础 NCA 训练接入真实动态数据，记录正式实验拆分与配置。
3. 实现 B2 小型 ConvGRU/ConvLSTM 时序对照；控制输入、预测长度与训练预算一致。
4. 实现 Proposed 的**最小差异化模块**，记录来自何种科学假设；做 1–2 个最关键消融，之后再扩展。
5. 至少记录一次失败/不稳定的真实例子并分析，不要只展示最漂亮样例。
6. README 加上清楚的模型框架图，不提前吹嘘超越 SOTA。

**验收**：真实的训练日志与 checkpoint 元数据；NCA 具备可重复预测与合理数值行为；各模型至少能在相同的固定测试集上运行。

### M4｜正式研究协议、对照、消融与结论

**任务**：

1. 锁定实验配置与样本划分，跑 Baseline vs NCA vs Proposed，并给出多 seed、不同 horizon/条件、可能的 domain shift 结果。
2. 指标与真实标签语义对应，输出每实验和整体统计，明确 `n` 与随机种子。
3. 保存失败/反例、数据少的风险、是否优于朴素基线、对照公平性。
4. 完成 `docs/research/results.md`、`limitations.md`、模型卡和可复现实验脚本。
5. 将实际研究图表加入 README，图下写清来源、测试集与模型版本。

**验收**：研究结论能被复算；不能编造“提升 20%”一类数值。

### M5｜正式软件后端与前端闭环

**任务**：

1. FastAPI 数据注册表、逐帧访问、实验结果、模型预测 job API 与任务状态；健康检查、版本标识。
2. 工作台接入真实数据与推理服务，读取预先训练好的权重，不在浏览器现场训练。
3. 展示原图、真实标注、预测、误差层及面积/边界曲线，具备可访问的键鼠交互和错误处理。
4. 后端单元/集成、前端组件测试与至少一条 E2E 链；UI 多次设计审查和性能优化。
5. README 加入真实的软件工作流截屏和后端架构图。

**验收**：新克隆可根据 README 完成基础部署，在满足数据/权重获取前提下运行真实完整预测链。

### M6｜研究扩展：模型内虚拟控制与可靠性分析（有价值才做）

**前提**：M4/M5 有可信的预测模型和稳定交互；若数据不足导致控制无意义，可用 ADR 降级为纯数值研究并明确限制，不强行追求“有画笔”。

**任务**：虚拟场参数、受预算约束优化、随机 baseline、A/B 情景快照、变化曲线、可选 uncertainty 检验、单元和 E2E。对界面 `IN-SILICO` 标签进行严格检查。

**验收**：优化策略的目标函数与预算约束可复算；绝不使用真实生物因果描述。

### M7｜发布打磨、讲解与最终答辩（后置）

**任务**：

1. README 最终编辑与真实截图、图解、双语材料、FAQ、局限、参考文献及贡献路径。
2. 从空环境克隆，按 README 命令验证；全量 CI、API、E2E、模型训练/评估复现。
3. 设计 3–5 分钟现场展示路线、可选 GIF/MP4 和教师操作脚本。
4. 代码清理、威胁模型与隐私检查、许可证、CITATION、GitHub Release、合理的 `v1.0.0` tag（达成范围时才发）。
5. 生成适合简历的一段真实项目介绍：研究问题、自主模块、公开基准、客观结果、代码与 UI 工程亮点。

**验收**：最终 GitHub 首页可信、优雅、可复现，版本内容与 tag 一致，历史可以从最初提交追到正式版本。

---

## 11｜进度记录、决策与沟通模板

### 11.1 每完成一条独立开发任务，Codex 需要维护的信息

```text
任务编号：
任务名称：
目标与完成条件：
本次实现/变更：
涉及的需求/研究假设：
测试命令与结果：
Git commit SHA：
GitHub push：成功/失败 + 对应远端 SHA/URL：
已知问题与后续处理：
```

不要求每个小 commit 都写一个几百字的 Markdown 文档；可把简要追踪存到 `docs/development/progress.md` 或相关 Issue，阶段结束再做完整总结。**切忌为了保存“工作记录”导致无意义的空提交循环**。

### 11.2 每阶段完成后向用户汇报（必须实事求是）

```text
【MorphoLab 阶段报告】M?
本阶段目标：
完成的真实功能：
页面/测试/研究证据（具体文件）：
实际运行的命令与结果：
数据源与授权：
科研结果（如无，写“尚无结果”）：
本阶段提交：SHA 列表 / GitHub 可访问链接：
远端同步：逐提交已核对 / 存在阻断（解释）：
现在的 UI 截图：路径（若尚未有真实页面，写无）：
遇到的问题与处理：
下个阶段计划与是否需负责人决策：
```

### 11.3 Codex 自主范围与必须请示的选择

**可自主决定**：函数/模块命名、一般实现细节、类型检查、UI 小幅布局调整、测试工具组织、重构、微小依赖更新、commit 拆分。  
**必须报告后再做重大变更**：主数据集由果蝇胚胎转到体外划痕、监督任务由 mask 变面积、放弃 NCA、改成纯模拟项目、引入付费 API/云服务、研究结论需要重新定义、数据许可尚无结论却要公开样本、公共仓库权限/所有权改变。

---

## 12｜Codex 接收文档后的首轮具体行动：只做启动阶段，不要开工大爆炸

这是接到本文后的**第一批动作**，不应一口气跨 M-1、M0、M1 把项目生成为大杂烩：

**Step 1｜检查环境和当前目录**  
列出必要开发工具是否可用；确认当前目录是新项目目录、没有误改已有仓库；判断 GitHub CLI 是否安装和登录。若无法使用 GitHub，只汇报阻断与需用户执行的安全授权动作；不得装作已完成远端同步。

**Step 2｜写项目最小真实文档**  
创建 `README.md`、本地 `.gitignore`、`AGENTS.md`、`docs/project/vision.md`、`docs/project/roadmap.md`。README 解释**是什么、为什么、准备如何研究、当前尚未完成什么**。文笔直接、清晰、克制，不要广告语言。

**Step 3｜初始化 GitHub，提交并推送第一次真实 commit**  
严格按照 §08 创建公开仓库；执行 commit → push → SHA 验证，保存可访问的 repo URL。新仓库不要先加 GitHub 网页初始化 README 再造成远端历史冲突。

**Step 4｜建立 M0 数据审计任务**  
开始核查 Zenodo 7660424 的许可与文件结构，确认公开下载，记录必要的原始链接；同时安排 GigaDB/BBBC019 的区别核查。只下载你确实需要的公开文件；大文件放在 `.gitignore` 内。

**Step 5｜先提交第一批真实的研究工具与单元测试**  
按最小独立改动依次实现 `datasets/registry.yaml`、审计 CLI、数据字段 schema、时间序列读取或文件清单工具；每个有意义的 commit 立即 push。脚本实际可执行，测试真实通过后更新 README 的已支持功能列表。

**Step 6｜停在可审查的节点，给用户一份阶段报告**  
报告数据到底下载/解析到什么程度、GitHub URL、commit SHA、许可证和标注语义风险、下一步应该实施的里程碑。**不要只回复“我已经搭好一个完整项目了”或者交付一堆从未运行的源代码。**

---

## 13｜必须主动查阅和正确致谢的参考资料

### 13.1 研究与算法

- Mordvintsev, Randazzo, Niklasson, Levin, **Growing Neural Cellular Automata**, *Distill*, 2020. https://distill.pub/2020/growing-ca/ 。NCA 的经典局部规则/生长与再生**是已有成果**，本项目不得据为己有。
- Google Research self-organising systems，https://github.com/google-research/self-organising-systems 。用于学习相关思想、比较实现；**不要直接拷贝整套项目当自主模块**。
- Stovold, **Neural Cellular Automata Can Respond to Signals**, 2023. https://arxiv.org/abs/2305.12971 。提醒“外部条件响应”已有研究。
- Zaritsky et al., **Live time-lapse dataset of in vitro wound healing experiments**, 2015. https://doi.org/10.1186/s13742-015-0049-6 。体外划痕数据语义，不能与果蝇 in vivo 直接混淆。
- 对象为真实伤口边界的近期预测研究，需要 Codex 在 M0 检索补齐；不要只引用 NCA 的经典文章，就说本项目具备新颖性。

### 13.2 数据

- Backova et al., **Videos of Embryonic Wound Healing in Drosophila and Wound Segmentation**, Zenodo, 2023. https://doi.org/10.5281/zenodo.7660424 。**首选主数据源**，其许可须再核验。
- GigaDB dataset 100118: https://gigadb.org/dataset/100118 。**不同体系的次级数据源，逐帧可取得性待核实**。
- BBBC019v2: https://bbbc.broadinstitute.org/BBBC019 。**静态图像与 ROI 资源，CC BY 3.0**。
- Zenodo restricted record 21031330: https://zenodo.org/records/21031330 。**明确排除作为无需授权可直接用的数据源**。

### 13.3 工程工具官方文档

- GitHub CLI 仓库创建：https://cli.github.com/manual/gh_repo_create ；授权：https://cli.github.com/manual/gh_auth_login 。
- React：https://react.dev/ ；Vite：https://vite.dev/ ；FastAPI：https://fastapi.tiangolo.com/ ；PyTorch：https://pytorch.org/docs/stable/ 。
- GitHub Docs（README、Actions、仓库安全）：https://docs.github.com/ 。

---

## 14｜最终交付的 Definition of Done（全部可证明）

### 科研

- [ ] 公共可访问的真实动态数据源已通过下载/结构校验，有来源、许可、标签定义、实验级分组证据。
- [ ] 至少一个经典机制 Baseline、一个简单深度学习 Baseline、基础 NCA 和拟议方法可复现。
- [ ] 对比/消融/失败样本透明；没有泄漏、伪造实验、夸大模型内干预的现实意义。
- [ ] 重要结果可从代码、配置、随机种子、数据版本和提交 SHA 追溯。

### 工程

- [ ] 项目可以从 GitHub 新克隆，并按 README 的实际命令运行必要的最小功能。
- [ ] Python/TypeScript 质量检查、关键单元/集成/E2E 完整通过；未运行项目不声称可运行。
- [ ] 软件的主流程不依赖商业 LLM 或神秘私有数据。
- [ ] 每个重要模块都有真实测试和清楚边界，无大而空的脚手架工程。

### 产品设计

- [ ] UI 具有专业可信的原创视觉语言，精致、克制、强层级；不呈现明显 AI 模板味。
- [ ] 数据来源、标注、预测、虚拟干预分别可辨；操作有正确反馈。
- [ ] 页面截图来自真实浏览器运行，非 AI 生图、非 Photoshop 效果图替代。
- [ ] README 图文并茂，引用完整，未实现功能不会被包装成已实现。

### GitHub 开发全过程

- [ ] 仓库是 Codex 从零实际创建的公开仓库，第一条 commit 是真实项目起点。
- [ ] **每一条本地 commit 都在完成后立即推送并核验远端 SHA**，无批量补交、假提交或重写历史。
- [ ] commit 内容围绕真实模块/修复/研究决策，能看出清晰递进过程。
- [ ] Issues/ADR/测试结果/README 变化与历史对应，任何关键设计取舍可追踪。
- [ ] 源数据与秘密没有误推公共 GitHub；最终 release 只包含许可明确内容。

---

## 15｜最后再强调一次：这份任务书最希望你做对的事

Codex，请把 MorphoLab 当作一个值得放进**本科生保研简历与夏令营项目经历**的长期工程来对待。技术路线不追逐最前沿的大模型，而是扎实地使用神经细胞自动机、CNN、时序建模、优化和完整的软件工程方法，把真实生物数据转化为可信的研究与可交互的产品。

**优先顺序永远是：真实公开数据 → 可信研究问题 → 可运行工程 → 高级且真实的界面 → 可复现实验和 README → 后期展示打磨。**

**从今天第一条 commit 开始让 GitHub 看到项目如何一步步长出来。** 你要自己写代码、自己运行检查、自己 commit、自己 push、自己核验。重要研究变更需要有据可依；无法证实的内容，明确写“未核实”。不要为了好看而编造、为了赶工而跳步、为了提交次数而制造虚假工作量。

**现在请严格执行第 12 章首轮行动，从 M-1 开始。**
