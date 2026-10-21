# 时序数据契约

实现为独立 Python 包 `morpholab_ml.data`；根 uv 项目以可编辑方式安装 `ml/morpholab_ml`，不依赖 HTTP、界面或数据库。来源为总任务书 §03.6。

`FrameRecord` 记录序列内索引、源帧索引、可为空的分钟时间和物理标尺、实际宽高、原图/注释的安全相对路径与编码文件 SHA256。注释类型必须明确为 skeleton / junction_skeleton / boundary / region_mask；未知类型拒绝，而不自动当 mask。

真实影像标记 `REAL_OBSERVED`。注释来源另分 source_annotation / derived_annotation / manual_annotation，并保存文字来源；由闭合边界填充而来的区域必须标记 derived_annotation，不能叫原始人工 mask。文件 SHA256 是 PNG/TIFF 等编码文件字节的 hash，不是解码后数组的 hash。

`SequenceRecord` 要求连续递增的序列索引与源帧索引、已知时间严格递增、尺寸一致。抽帧不能靠重编号冒充连续。`grouping_basis` 区分有独立实验依据的分组与仅以源序列代理的分组；后者不证明生物独立性。`unassigned` 可用于审计，但训练入口必须调用 `validate_trainable()` 并拒绝它。

`DatasetCollection` 拒绝重复 sequence ID 和同 experiment 跨 split。`validate_files(root)` 实际检查文件存在、解析后仍处允许根目录内、文件 hash 与 Pillow 解码尺寸。该契约不单独证明序列近重复不存在；跨序列像素重复与近重复属于内容审计和实验划分 QC。

所有记录禁止额外字段和非有限数值。构造模型不读取磁盘；文件验证为显式操作，便于离线使用和测试。

本地真实符号链接测试因 Windows 权限不足可能显式跳过；解析越界拒绝另有不依赖 symlink 权限的测试，Linux CI 继续验证真实 symlink 情境。
