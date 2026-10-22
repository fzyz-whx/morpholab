# 实验协议状态

数据、模型与预算已冻结，12次真实训练及正式test评价完成。主域、监督、QC、工作网格、初始L/H和独立划分见 [ADR-0001](../project/decisions/ADR-0001-observed-domain-target-and-split.md)。模型与600步×3seeds预算见[ADR-0002](../project/decisions/ADR-0002-local-models-and-training-budget.md)，匹配窗口H1消融见[ADR-0003](../project/decisions/ADR-0003-matched-window-horizon-ablation.md)，实际结论见[results](results.md)。

协议名 `morpholab-split-v1`，不是作者44/12/5复现。以源序列为分组代理，Test名称的五条仅作为保守独立holdout；其余57条用固定名称hash选12条validation、45条train。每帧继承序列split。正式清单由工具生成并保存hash，训练入口不接受未分配序列。

只对经过严格QC的薄轮廓生成派生区域/距离场，失败帧不修补、不插值、不压缩时间；排除包含失败帧的窗口。未知物理时间和标尺保持null；指标以64×64工作网格pixel或pixel²报告。

矩阵为Persistence、恒速几何基线、ConvGRU、基础NCA、正则NCA及H1监督NCA。所有神经模型使用同历史摘要、相同600步与batch8、seed17/29/43；每100步按validation多步监督损失选best。主训练H12，验证/测试H24；H1仅监督前缀，仍保持H12候选池。参数量和实际算力不完全相等，全部成本与局限公开，未作严格等FLOPs因果声明。

主评价L4/H24/stride12，先窗口→源序列、再序列等权→seed，最后报告三个seed均值与ddof1样本SD。敏感性L2/4/8共享8帧QC块与forecast origin=start+8，取末L帧、相同未来；不是不同L各自调优重训。官方split与生物批次未知；不把重叠窗口或seed当独立实验。

任何后续更改需写明原因和新协议版本。test仅用于最终锁定模型评价，不用于选择损失、超参或约束。多seed报告实际次数，每实验配对比较，披露有效窗口数、QC排除、失败案例和负结果。
