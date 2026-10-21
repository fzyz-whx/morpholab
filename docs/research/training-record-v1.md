# 正式训练记录 v1

2026-10-21 UTC完成的12次真实训练均来自干净且已同步的源码
`056332d083de1527e49342772ecf2ef974813959`。不是合成fixture，也不是最后补写的训练成绩。
完整预算、选中步骤和检查点哈希见[机器可读记录](results/training-budget-v1.json)。

- 基础NCA、更新幅度正则NCA、小型ConvGRU、H1监督NCA各seed17/29/43；每次600步、batch8。
- 45条train序列，12条validation序列；正式训练不打开test数组。
- 相同历史摘要输入L4，主训练监督H12；H1消融仍保持H12候选池，仅监督前缀1步。
- 每100步按validation多步监督损失选择best；不按test或展示效果挑seed。
- RTX5060 Laptop、PyTorch2.11.0+cu128、IEEE fp32、确定性算法；实际版本与峰值allocated显存记录在每次run元信息中。
- 所有run均完成，未发生NaN/Inf或训练中断。预算总量7200步，实际优化与validation运行耗时合计676.422秒，非总开发时间或整机占用时间。

原始运行使用顺序内联驱动器直接调用已冻结的`train()`，并在每次运行前检查Git清洁状态；
没有把后加入的批量CLI冒称为当时的执行脚本。现在可用以下命令重新生成同配置矩阵，输出必须是新目录：

```sh
uv sync --locked --extra cpu
uv run --locked --extra cpu python scripts/train_matrix.py --device cpu --output artifacts/training/reproduction-v1
```

兼容NVIDIA环境可以把extra和device都换为`cuda`。CPU与CUDA不是逐位相同的硬件环境，
该命令未在CPU上重新跑满7200步；CPU的保存、恢复、梯度与合成短训另有自动化检查。
失败时保留已有运行与failed矩阵，不覆盖、不静默跳过、不继续训练后面的seed。

单独重跑一个配置使用`scripts/train.py`，H1需明确传入
`--config ml/configs/forecast-h1-ablation.yaml --model nca`。
这里的validation损失只能用于选检查点，不能据此宣布NCA优于对照；正式test结论另行冻结评价。
