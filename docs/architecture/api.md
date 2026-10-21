# 本地只读数据 API · v1

M1提供真实观测与原始薄轮廓浏览，不运行训练、预测作业、下载或数据修改。主研究域与派生目标见[ADR-0001](../project/decisions/ADR-0001-observed-domain-target-and-split.md)。模型状态固定为 `untrained`，不存在未来影像接口。

从仓库运行：

```powershell
uv sync --locked
uv run python scripts/serve.py
```

入口固定监听 `127.0.0.1:8765`；数据根目录按源码位置解析，服务不依赖工作目录。Vite开发界面将 `/api` 代理到该地址，无需开启跨域访问。服务只有GET读取接口，OpenAPI位于 `/docs`。

## 路由与元数据

| GET路由 | 内容 |
|---|---|
| `/api/v1/health` | 服务状态、真实本地数据可用性、数据问题码、未训练状态 |
| `/api/v1/datasets` | 已登记的数据源，包括尚未本地取得的候选源 |
| `/api/v1/datasets/{dataset_id}` | 单个数据源的真实来源、许可、计数及本地状态 |
| `/api/v1/sequences?dataset_id=...` | 指定数据源的序列；默认主数据源 |
| `/api/v1/sequences/{sequence_id}` | 序列元数据与连续帧列表、QC状态、显示处理说明 |
| `/api/v1/sequences/{sequence_id}/frames/{frame_index}?layer=...` | PNG显示图层；零起始帧索引 |

主数据源ID为 `drosophila_wound_zenodo_7660424`。序列ID来自公开审计摘要白名单，例如 `WH01`、`WHu01`、`Test01`，不接受任意文件路径。

所有业务JSON响应（含错误）统一包含 `schema_version:"1"`、`provenance`、`dataset_id`、`model_id:null`、`run_id:null`、`created_at_utc`。时间字段是本次响应生成的UTC时间，不是实验采集时间。健康和来源目录metadata的provenance为null；数据源列表dataset_id为null，单数据源详情为对应ID；序列列表/详情为对应dataset_id与 `REAL_OBSERVED`。错误中无法确认的来源字段为null。列表保留 `items:[...]`，详情保留现有顶层字段。

数据源字段：`id`、`name`、`biology_domain`、`domain`（前者别名）、`source_url`、`doi`、`license`、`sequence_count`、`frame_count`、`local_available`、`annotation_type`、`model_status`、`reported_frame_interval_min`、`verified_frame_interval_min`、`official_split`。未下载候选源的未知计数为null，不根据页面描述伪造本地计数。

序列字段：`id`、`dataset_id`、`frame_count`、`height`、`width`、`image_dtype`、`annotation_type`、`project_split`、`official_split`、`qc_valid_count`、`qc_definition`、`timestamp_min`、`provenance`。项目划分来自冻结的 `datasets/splits/morpholab-split-v1.json`，不存在时为 `unassigned`；官方划分始终为null，不能把项目test误称官方test。

详情增加 `frames:[{frame_index,timestamp_min,qc_valid,touches_border}]`。优先使用本地预处理manifest中完整的ADR-0001目标QC，包含64×64目标退化检查；尚未预处理时仅显示原始闭轮廓及触边检查，`qc_definition`明确标记source-only。失败帧保留原索引且仍可浏览。物理时间始终为null，发布者报告一分钟采样另列，不能当已核实逐帧时间。

## 图层与真实性

`layer`只接受以下值：

- `observed`：原始uint16观测经整条序列的1%/99.5%分位对比度映射到8-bit显示；源TIFF未修改。这是显示映射，不是训练归一化。
- `annotation`：原始注释的非零薄轮廓显示为白线，背景黑色；不填洞，不宣称原始人工区域GT。
- `overlay`：观测显示图加原始薄轮廓，颜色为 `#D4DCA5`，与界面ANNOTATION图例一致。

PNG带 `X-Provenance: OBSERVED|ANNOTATION|OBSERVED+ANNOTATION`、`X-Derived-Display: true`、`X-Annotation-Provenance: source_annotation`。`X-Source-Dtype`在annotation层为uint8，在observed/overlay层为原观测的uint16。另以 `X-Schema-Version`、`X-Dataset-Id`、`X-Source-Id`、`X-Sequence-Id`、`X-Frame-Index`标识接口版本和来源，不向PNG混入JSON字段。所有图层都是显示产物，不是用于回读科研数值的原始数组。响应不返回个人绝对路径。

## 缓存、安全与错误

首次读取前对完整ZIP核验公开摘要中的SHA256，并复用内容审计工具的成员路径、解压体积及TIFF尺寸限制。ZIP的size/mtime/ctime变化会使验证和序列缓存失效。内存最多保留4条解码序列，按LRU淘汰。只读取白名单成员，不展开ZIP，不执行归档内容。

`health`返回200仅表示状态端点可读；只有 `data_available:true` 表示归档校验及本地审计可用。缺缓存或审计时可返回degraded；影像请求返回503，并提供以下无个人路径的恢复命令：

```powershell
uv run python scripts/download_data.py
uv run python scripts/audit_data.py
```

错误在公共JSON信封内保留 `error:{code,message,details,trace_id}`。非法序列/帧为404，非法图层或类型为422，不支持的方法为405。服务器不回显异常中的本机路径或输入内容。当前只支持本地受控数据浏览，无预测job、鉴权或公开部署。

## 检查边界

`uv run pytest -q backend/tests` 使用临时合成TIFF/ZIP验证读取、PNG、错误、校验失效、LRU、索引、划分与QC；这些fixture不属于科研数据。真实数据还需单独执行API与界面验收，不能把TestClient或HTTP200当端到端验收。
