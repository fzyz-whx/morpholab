# 可复现形态数据管线

执行：`uv run --locked python scripts/prepare_data.py`。输入为已固定SHA256的Zenodo压缩包，输出位于忽略的 `artifacts/processed/`；失败非零退出。依据 [ADR-0001](../project/decisions/ADR-0001-observed-domain-target-and-split.md)。

纯计算 `morpholab_ml.data.preparation` 仅接受数组，不依赖归档、网络或应用。CLI负责安全ZIP读取、源成员hash、分组冻结、压缩NPZ原子写入和元数据。每序列保留全部原始时间点，不能通过压缩无效帧来制造连续时间。

## 产物

- `manifest.json`：来源hash、协议、QC定义、45/12/5项目划分、逐序列有效帧/排除索引、NPZ相对路径和文件hash、所有数组shape/dtype、可用窗口数。
- `sequences/<id>.npz`：uint16原图、uint8源轮廓、native派生区域、64×64区域/SDF、valid布尔标识和原帧索引；读取时使用 `allow_pickle=False`。
- 仓库 [固定划分](../../datasets/splits/morpholab-split-v1.json)：仅源ID、hash与明确命名的项目协议，官方split仍为null。
- `near-duplicate-screen.json`：首/中/末16×16中心化缩略图的启发筛查，阈值0.995；候选不是已证实重复，零候选不证明生物独立，也可能漏过平移、裁剪或不同采样。

## 转换与QC

原注释只接受统一0/1或0/255。归一化非零轮廓通过单组件、无端点/分支、单封闭洞且不触边检查后填充区域。128→64采用最近像素中心，工作区域空/全满也拒绝。SDF内部正，欧氏距离差裁剪±8后除8，标记 `DERIVED_ANNOTATION`。

无效目标数组有零占位，仅供保持时间维；消费者必须检查valid。`window_starts`只返回整个L+H跨度都有效且连续的窗口，不跨坏标签，不丢掉源帧后重编号。

## 已运行证据

62条、7229帧完整处理，7183有效，46无效；原生闭轮廓/不触边7184帧中另有1帧在64网格区域消失。所有原图和原轮廓保留。固定划分45 train / 12 validation / 5 test，不是作者44/12/5复现。

第二次全量重跑核对manifest、freeze与62个NPZ的SHA256逐字节相同，并独立 `np.load(..., allow_pickle=False)` 回读有效数及源索引。manifest SHA256：`a04b3a66c9fb910c6f3b180e5ce22ca185e721daeacda19433fde3f82fea6ce0`；划分文件SHA256：`32977b94af19cc5f5ae628ff3c5484b8830366fbaabaaa77560253570ccce625`。

近重复启发筛查候选0；原审计的影像精确重复也为0。两者仍不构成已排除所有数据依赖/预训练污染的保证。本项目尚未训练任何模型。
