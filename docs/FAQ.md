# 常见问题

## 可以预测真实显微图像吗？

当前预测的是历史注释条件下的64×64形态。显微灰度是OBSERVED原帧，预测叠加是PREDICTION；不是由网络生成的未来图像，也没有自动分割模块。原始注释是薄轮廓，计算目标是明确标记的DERIVED_ANNOTATION。

## 为什么有62条，而论文/发布页说61条？

实际压缩包有62对可解析TIFF。缺少作者排除清单和官方split映射，不能擅自删除一条凑数。本项目公开45/12/5独立协议，保留这个差异。[审计](research/data-audit.md)列出证据与未知项。

## 没有GPU或不想安装Torch怎么办？

`uv sync --locked`足以下载、审计、准备数据、浏览和运行经典基线。独立worker也可执行经典方法。神经预测需要`--extra cpu`，不需要GPU。
CUDA只用于兼容设备上的可选训练/评价；CPU与CUDA extra互斥。切换仅影响本项目虚拟环境。

## 页面打开但没有数据、模型或作业一直排队？

打开`/api/v1/health`分别查看`data_available`、`model_status`与`worker_ready`，HTTP200不代表所有部分就绪。
数据需要download→audit→prepare三个步骤；神经模型需要安装cpu或cuda extra及通过哈希验证的权重。
使用`scripts/serve.py`默认同时管理独立worker；若用了`--no-worker`，另开`scripts/worker.py`。
异常堆栈只在worker本机日志，网页显示安全错误。缺模型不会自动联网训练或生成占位预测。

## 可以复用已核验的本地缓存吗？

可以。进程环境`MORPHOLAB_ARTIFACTS_ROOT`指向包含`raw/`、`audit/`、`processed/`、`training/`的artifacts根目录；服务只读来源文件，任务数据库仍写在当前项目的`artifacts/app`。

```powershell
# PowerShell示例；将该示例路径替换为自己的已核验缓存
$env:MORPHOLAB_ARTIFACTS_ROOT = 'D:\MorphoLabArtifacts'
uv run --locked --extra cpu python scripts/serve.py
```

```sh
# Linux示例
MORPHOLAB_ARTIFACTS_ROOT=/path/to/verified-artifacts uv run --locked --extra cpu python scripts/serve.py
```

研究CLI不隐式读取这个服务环境变量；明确传`--manifest`和`--matrix-root`，便于检查实际研究输入。
新克隆验收会明确说明是否复用缓存，不把共享缓存冒称为重新从零下载。

## 下载器拒绝覆盖已有训练目录？

这是预期保护。若现有科学文件与固定发布包完全相同则复用；不同则拒绝替换，保护已有实验。
可用`--artifacts`选择新根目录，或使用原训练结果自行评价。不要为安装模型删除尚未保存的实验。
离线安装支持`--archive <本地发布包>`，同样验证整个ZIP和39个成员，不执行内容。

## 为什么有些帧没有指标，预测还在？

历史QC必须有效；未来原注释若不满足可靠派生目标条件，仍可显示原图并产生预测，但目标与指标为null。
不能补线或删除该时间点来制造完整真值。当前起点+L+H须在记录帧内。

## 为什么IoU较高，边界距离反而更差？

指标关注不同误差；提前闭合的空预测尤其影响边界距离。只有一侧边界为空时保留90.509668工作网格pixel惩罚，不能丢掉这些失败。
当前NCA H24 IoU高于Persistence，但平均边界距离更差。请同时阅读多指标和[失败案例](research/forecast-results-v1.md)。

## 为什么不做画笔或“智能干预”？

数据没有受控干预标记，也没有可验证的生物控制参数。任意隐状态优化可降低模型目标，不代表现实有效。
按总任务书M6条件闸门，本版只保留输入长度数值敏感性，不实现未经验证的控制；见[ADR-0004](project/decisions/ADR-0004-defer-control-and-bound-reliability.md)。

## 如何重跑而不破坏正式报告？

选新训练/评价输出目录，提交并同步源码后再运行。默认评价validation，test必须显式指定。
公开报告生成器会写指定目标；探索结果应明确传`--output`、`--markdown`和`--figures`到忽略目录。
新硬件或代码的Git/环境/hash不同，应作为新运行记录，不能修改原始元信息伪装成同一次实验。
