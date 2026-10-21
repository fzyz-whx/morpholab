# 相邻工作与重复风险

核查日期：2026-10-21。本文是 M0 文献与官方元数据核查，不证明数据已下载或模型已复现。MorphoLab **未训练、未评估**；主研究域暂定果蝇胚胎 **in vivo 激光创面闭合**。以下差异是待检验问题，不是创新结论。

## 相邻工作矩阵

| 工作与已核查证据 | 已有成果与任务边界 | MorphoLab 可检验的问题 | 重复风险 |
|---|---|---|---|
| Mordvintsev et al., [Growing Neural Cellular Automata, Distill 2020](https://distill.pub/2020/growing-ca/)；作者正文 | 局部共享可微更新、目标图案生长、持续状态与损伤后再生；图案实验不是本项目的真实显微序列预测 | 用真实观测初始化后，局部递推能否保持远期预测精度和数值稳定 | 局部更新、自组织、持续训练与再生均已有；不能把 emoji 换创面称为贡献 |
| Stovold, [Neural Cellular Automata Can Respond to Signals](https://arxiv.org/abs/2305.12971)，2023 / v2 2024；作者摘要 | 内部信号选择形态、外部信号改变颜色；展示 NCA 条件响应 | 在有实测依据的观测条件下，比较初始化或更新条件化；不虚构生物条件 | “NCA 能接受外部输入/响应干预”不是新颖性；摘要不能证明其真实创面预测性能 |
| Backová et al., [ISBI 2023 作者论文](https://danifranco.github.io/files/2023/biofisika/10230571.pdf)，[研究组出版页](https://cvpd.github.io/publication/backova-2023-modeling/)；已读取 PDF 文本 | 同主数据体系的真实果蝇创面视频预测；VQ-VAE + 自回归 Transformer，详见下文 | 与通用时序模型公平比较局部规则的长期误差、失败率及成本 | **直接相邻工作**；“前几帧预测闭合”以及同数据上的学习动力学早已做过 |
| [Building Self Regenerating System with Neural Cellular Automata, NOLTA 2026 / 9284](https://epapers2.org/nolta2026/ESR/paper_details.php?paper_id=9284)；官方录用摘要 | 页面为 Accept as Lecture；摘要称用实验数据训练局部共享 NCA，观测/潜在状态通道共同描述伤口动力学 | 取得全文及实验协议后，再比较数据、初始化、约束与长期评价设计 | **高度重叠警示**。目前仅有摘要；数据域、划分、监督、预算、结果均未核实，不能声称没有同类工作 |
| Johnston et al., [Fisher–Kolmogorov / IncuCyte, 2015](https://link.springer.com/article/10.1186/s12918-015-0182-y)；出版社正文 | 从体外 PC-3 划痕实验估计迁移扩散、增殖率与承载密度；连续反应扩散模型 | 简单前沿/机制基线是否已能解释可观测变化；参数只利用合法训练/验证信息 | PDE 伤口动力学与参数估计已有；其细胞密度及增殖假设不能直接套到果蝇收缩环 |
| Suarez-Arnedo et al., [Wound Healing Size Tool, PLOS ONE 2020](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0232565)；作者论文 | ImageJ/Fiji 的体外划痕图像/堆栈分割与面积、宽度量化 | 作为测量和人工 QC 参照；验证目标量的可重复测量性 | 测量已有影像不等于预测未来；软件 UI 和面积曲线也不构成新算法 |

## 与 Backová 2023 的具体比较

该文与 [Zenodo 7660424](https://zenodo.org/records/7660424) 对应：61 条序列，官方 train/validation/test 为 44/12/5。模型预测显微视频，而非仅做单帧分割。论文 §3.2 用 128×128、20 帧训练片段：8 帧上下文预测 12 帧，再用最后 8 张预测帧递归生成后续，直到测试序列结束。§3.3–3.4 的平均边界距离及 Hausdorff 距离定量覆盖最初 20 帧；全程另看归一化面积趋势。不能把它描述为“只预测下一帧”，也不能把短窗边界成绩当全程误差。（依据上述作者 PDF，pp. 2–4。）

其影像分割由网络辅助并人工修订；论文中的填充 mask 与公开附件的 skeletonized segmentation 是否一致，必须另行检查。MorphoLab 当前没有确定输出为 mask、边界、骨架或面积。若日后以更简化标签作输入/目标，必须标为不同任务；不能直接将指标与原论文作排行榜。需要重跑同输入、同划分、同预测时长与可比预算的对照；无法复现时只做文献比较，公开限制。

上述证据已否定宽泛的“首次用学习模型预测果蝇创面”叙述；NOLTA 摘要也使“首次用真实数据训练伤口 NCA”不可支持。当前可研究的是明确协议下的局部递推与最小约束消融，是否有增益仍未知。

## 次级数据源：官方元数据与获取边界

本节只记录入口核对，不替代独立的真实文件审计。未下载这些数据包，也未声称逐帧解析成功。

| 资源 | 官方证据与许可范围 | 本次可访问性与使用边界 |
|---|---|---|
| [GigaDB 100118](https://gigadb.org/dataset/100118) / [DataCite DOI 元数据](https://api.datacite.org/dois/10.5524/100118) | PowerShell 实际读取 DataCite `rightsList` 为 **CC0 1.0**；描述为 31 组、两细胞系体外时序实验。作者 [Data Note](https://link.springer.com/article/10.1186/s13742-015-0049-6) 区分 GigaDB 中间轮廓/运动场/脚本与 CIL 原影像；代码的 GPL v3 不能替代数据许可 | GigaDB 请求 HTTP 200，但 web 无可解析正文；DataCite JSON 可读。原图指向 [MDCK group 44501](https://www.cellimagelibrary.org/groups/44501) 和 [DA3 group 45451](https://www.cellimagelibrary.org/groups/45451)，本次 web 均超时；未验证原图逐帧下载，CIL 条目许可尚未逐项核对。CC0 元数据不等于当前原图链路畅通 |
| [BBBC019v2](https://bbbc.broadinstitute.org/BBBC019) | 官方列 171 张、八个子集及各 ZIP；逐图同名二值 PNG 人工标注，白色为 foreground。Copyright 明示 **CC BY 3.0 Unported**，要求署名；遵循官方推荐引用 BBBC019v2 与 Ljosa et al. | 页面和 ZIP 链接可见；未请求/解析 ZIP。用于静态测量/QC；页面没有提供可据以重建完整真实时间序列的时间映射，不能自行拼成视频或伪造未来真值 |

后续复查应保留取得日期、文件 hash、序列级分组和逐项授权依据；不同实验体系分别报告，不混合形成单一成绩。
