# MorphoLab Forecast v1 模型卡

**用途：** 本地科研教学、历史注释条件下的形态预测、经典方法与小型网络的可复算比较。
**不适用：** 真实临床决策、显微图自动分割、未来组织纹理生成、药物/基因/治疗因果分析。

## 数据与输入输出

Backova等2023，[Zenodo7660424](https://doi.org/10.5281/zenodo.7660424)，CC BY4.0。
果蝇胚胎in vivo激光创面闭合；62条、7,229帧。严格QC有效7,183帧。
45train/12validation/5test为本项目独立源序列协议，官方split未知。
数据署名和转换见[ATTRIBUTION](../../datasets/ATTRIBUTION.md)。

输入`float32[B,L,64,64]`为历史派生SDF，内部采用最后场与逐像素历史线性斜率摘要。
输出`float32[B,H,64,64]`，区间[-1,1]，正值表示派生创面内部。
模型从历史自由rollout，不回灌未来标签。当前评估H≤24；L2/4/8可运行但训练L4。

## 实现与训练

- NCA：16通道状态、固定identity/Sobel/Laplacian局部感知、共享1×1更新网络；14,622参数。
- 正则NCA：同结构，仅增加0.001实际状态更新平方惩罚，不解释为生物能量。
- ConvGRU：同历史摘要、16通道隐状态、残差输出；18,417参数。
- H1NCA：同基础NCA，H12候选池但只监督1步，用作多步监督消融。
- 每配置seed17/29/43、600步、batch8、Adam0.002、梯度裁剪1；H12主训练、H24validation。
- 每100步按validation序列等权监督损失选best。单个软件默认模型seed也只按validation选，不按test。

全部12次真实训练源码`056332d083de1527e49342772ecf2ef974813959`，git_dirty=false。
权重来源、best步骤、SHA256、预算、实际软件版本与设备见[正式报告JSON](results/forecast-test-v1.json)的runs。
安全加载仅限来源受控且SHA256匹配的checkpoint，PyTorch weights_only=True；不接受用户上传pickle。

## 评价与风险

正式test评价源码`a83ed4d054b57ecd379804e6e163c51dd9fbe000`，CUDA12.8、Torch2.11.0+cu128、IEEE fp32、确定性算法，44秒。
5条源序列代理、25个共同窗口；先窗口→序列，再序列等权→seed均值与样本SD。
NCA H24 IoU0.4596±0.0269；正则0.4612±0.0255；ConvGRU0.4128±0.0446；Persistence0.3368。
NCA边界距离仍差于Persistence，并会在创面实际未完全闭合时预测空区域。
正则收益很小，不足以支持强改进主张。完整多指标、消融与失败见[研究结论](results.md)。

无物理标尺、无准确时间、无可靠动物批次标记、无干预因果标签。性能不保证跨域泛化。
模型输出必须标PREDICTION；用于展示的真实未来图像必须标OBSERVED，不能冒称网络生成。
seed SD不是预测可信度。模型内控制与真实生物实验没有经验证的对应关系。

## 许可与发布

源码MIT；数据CC BY4.0并保留署名。权重与配置应随发布单独提供来源、hash与用途说明，不把源码MIT当作数据再分发许可。
原始显微影像、训练日志和权重不进入源码Git；当前是否有可下载权重以真实GitHub Release附件为准，未上传前不能说已发布。
