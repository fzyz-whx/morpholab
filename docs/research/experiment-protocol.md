# 实验协议状态

当前为数据协议冻结阶段，未训练、未评估。主域、监督、QC、工作网格、初始L/H和独立划分见 [ADR-0001](../project/decisions/ADR-0001-observed-domain-target-and-split.md)。

协议名 `morpholab-split-v1`，不是作者44/12/5复现。以源序列为分组代理，Test名称的五条仅作为保守独立holdout；其余57条用固定名称hash选12条validation、45条train。每帧继承序列split。正式清单由工具生成并保存hash，训练入口不接受未分配序列。

只对经过严格QC的薄轮廓生成派生区域/距离场，失败帧不修补、不插值、不压缩时间；排除包含失败帧的窗口。未知物理时间和标尺保持null；指标以64×64工作网格pixel或pixel²报告。

模型矩阵为Persistence、Classical、ConvGRU、Vanilla NCA与单一约束消融。此时没有冻结正式超参数或宣称预算已经匹配；待数据管线与数值fixture跑通后、查看test模型分数前记录最大训练步数、batch、seed、选模规则、horizon与资源成本。

任何后续更改需写明原因和新协议版本。test仅用于最终锁定模型评价，不用于选择损失、超参或约束。多seed报告实际次数，每实验配对比较，披露有效窗口数、QC排除、失败案例和负结果。
