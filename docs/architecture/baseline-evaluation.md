# 几何基线与评价实现

`morpholab_ml.baselines.geometric`和`evaluation.metrics`为纯计算层。输入是已声明的历史距离场，未来目标不传入预测器。CLI：`uv run --locked python scripts/evaluate.py`，默认validation、L=4、H=4/12/24、stride=12。

## 基线定义

- Persistence：将最后观测的距离场复制到全部未来时间点。
- Constant normal speed：由历史派生区域面积得到等效半径`sqrt(area/pi)`，以历史帧索引拟合半径斜率，截断在±2工作像素/帧；重建最后区域的完整有符号距离场后，以该速度平移，再裁剪±8并归一化。它是几何近似，不是实测生物力学参数，不预设伤口面积单调。

不能直接平移已经饱和的裁剪距离场，否则长期扩张可能把远处背景同时翻转。实现先恢复完整距离再演化。像素离散化允许亚像素运动下首个预测区域暂时不变；不会为使实验曲线更好看而强制每帧缩小。

## 指标与失败

对相同64×64二值派生区域计算IoU、Dice、面积绝对/有符号误差。边界为4连通腐蚀得到的内数字边界；两个方向的最近边界距离合并后计算均值和95百分位Hausdorff距离。距离单位为工作网格pixel，面积为pixel²。

两侧均为空：IoU/Dice=1、边界距离=0。一侧为空：IoU/Dice=0，边界距离赋网格对角线的有限惩罚，并标记`empty_boundary_mismatch`。这是明确的失败约定，不把未定义距离偷偷删出均值。NaN/Inf或尺寸不合法直接失败。

## 数据、窗口与汇总

研究CLI只接受完整62条源清单；计算库可使用明确标为partial_source_manifest的合成/子集测试清单。校验源协议、实验组/项目split、编码文件hash、相对路径、实际数组dtype/shape/finite、原帧索引及valid掩码。仅加载所选split的NPZ；不读取test数组来计算validation。

所有H共用最长H的完整连续有效窗口，预测器每窗口仅收到历史副本。保存每window与lead 1–24的分数；endpoint为4/12/24。先在序列内平均窗口，再对序列等权，报告序列数和窗口数、QC排除，不能把每帧当独立实验。

## 产物与可追溯性

每个新目录保存run.json、逐lead CSV/JSON、逐序列与总汇总、最差案例JSON/PNG。元信息记录Git SHA、全工作树dirty状态、关键实现文件SHA256、源manifest SHA256、配置、依赖、实际时间和来源。图像明确区分历史/未来派生标签与预测。

源码提交前的validation执行只算dirty pilot，不补造当时缺失的来源hash。提交、push并核对后，从干净工作树重跑才形成可引用的正式validation记录。当前不通过调整恒速参数追逐pilot成绩，此处保留validation阶段记录；随后已按冻结协议评价正式test，见[结果](../research/results.md)。
