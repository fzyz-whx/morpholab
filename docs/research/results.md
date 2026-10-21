# 研究结论与证据索引

这是限定数据、标签与预算下的探索性比较，未进行显著性检验，也没有论文新颖性或临床性能主张。
完整数值、配置、每序列结果、权重哈希与全部曲线见[正式test报告](forecast-results-v1.md)及[JSON](results/forecast-test-v1.json)。

## 问题与实际协议

输入是L4历史注释派生的64×64距离场，输出为未来1–24帧形态。不是自动分割灰度图，不生成显微纹理。
采用独立的45/12/5源序列分组；官方文件映射未知。train不打开test数组，按validation损失选checkpoint。
每个神经配置seed17/29/43各600步；test使用5条源序列、每方法/seed共25个共同窗口。
窗口先在源序列内平均，再序列等权；表中±为训练seed的样本SD，不能当生物置信区间。

| 方法 | H4 IoU | H12 IoU | H24 IoU |
|---|---:|---:|---:|
| Persistence | 0.7645 | 0.5629 | 0.3368 |
| 恒法向速度 | 0.7819 | 0.5082 | 0.2691 |
| ConvGRU | 0.7808±0.0017 | 0.6665±0.0086 | 0.4128±0.0446 |
| NCA | 0.7994±0.0061 | 0.6587±0.0067 | 0.4596±0.0269 |
| 正则NCA | 0.7996±0.0076 | 0.6591±0.0069 | 0.4612±0.0255 |
| H1监督NCA | 0.7857±0.0021 | 0.5839±0.0022 | 0.3376±0.0264 |

## 假设得到怎样的支持

**局部更新的远期优势：只有有限、依指标而定的支持。** NCA的H24 IoU均值高于ConvGRU约0.0468、
高于Persistence约0.1228，但H12低于ConvGRU。NCA的H24平均边界距离为4.152工作网格pixel，
仍差于Persistence的3.624；面积误差则明显较低。不能用单个IoU概括全面胜出，不能从5个代理组推断总体优势。

**更新幅度惩罚：没有令人信服的额外收益。** H24 IoU仅比基础NCA高约0.0016，远小于跨seed波动；
面积MAE与平均边界距离略差。当前0.001权重不支持“稳定性改进已成立”的表述。
没有在看test后搜索正则权重来追分。

**多步监督：本预算下的现象支持其必要性，但不是等算力因果证明。** H1监督NCA的H24 IoU接近Persistence，
面积MAE更大，完整H12监督效果更好。H1仍使用相同H12采样池与相同600步，但实际计算时间更少；
因此不能解释成严格等FLOPs下的收益。该对照在真实训练前由ADR-0003预注册。

## 稳健性与失败

共同origin=start+8的L2/4/8敏感性中，NCA的H24 IoU约0.4089/0.4390/0.4251，
没有“历史越长越好”的单调规律。所有模型训练时L4，这属于输入条件敏感性，不是对每个L重新训练的最优比较。
其L4与主评价起点不同，不能混用两张表。

最差窗口按所有seed与窗口的H24最小IoU自动选择。NCA在Test01、origin76、seed43的目标仍有小创面时预测空区域，
展示了提前闭合失败；此时边界距离保留有限惩罚而非删除失败样本。
恒速也存在提前闭合，Persistence则容易保留过大的旧区域。完整报告同时保留六种方法的最差案例，未只挑好看的展示。

没有可靠批次、动物、物理尺度或干预标记，因此未声称完成跨动物、跨实验室或跨域泛化。
GigaDB属于另一生物域，不强行混合成额外测试集。

## 复算

```sh
uv sync --locked --extra cpu --extra reports
uv run --locked --extra cpu python scripts/train_matrix.py --device cpu --output artifacts/training/forecast-v1
uv run --locked --extra cpu python scripts/evaluate_models.py --split test --device cpu --output artifacts/experiments/forecast-test-reproduction
uv run --locked --extra cpu --extra reports python scripts/report_forecasts.py --evaluation artifacts/experiments/forecast-test-reproduction
```

先按README下载、审计和预处理数据；输出目录必须不存在。完整训练需干净源码、完整Git历史和足够时间。
原始训练由顺序内联驱动完成，批量CLI为随后加入的复算入口；没有冒称后加脚本是原始执行命令。
原始正式评分使用CUDA、干净源码`a83ed4d054b57ecd379804e6e163c51dd9fbe000`，耗时44秒；
CPU命令是支持路径，不声称CPU重跑所得逐位相同。重跑会产生新的Git、环境、时间与权重hash，不能覆盖原始元信息。

更多边界见[局限](limitations.md)与[模型卡](model-card.md)。
