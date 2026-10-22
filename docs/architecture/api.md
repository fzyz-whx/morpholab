# 本地科研工作台 API · v1

提供真实观测、原始薄轮廓浏览与持久化形态预测作业；不触发训练或自动下载。主研究域与派生目标见[ADR-0001](../project/decisions/ADR-0001-observed-domain-target-and-split.md)。模型就绪状态读取实际矩阵与校验权重；不存在生成未来显微纹理接口。

从仓库运行：

```powershell
uv sync --locked
uv run python scripts/serve.py
```

入口固定监听 `127.0.0.1:8765`；数据根目录按源码位置解析，服务不依赖工作目录。Vite开发界面将 `/api` 代理到该地址，无需开启跨域访问。OpenAPI位于 `/docs`。神经推理需安装cpu或cuda extra；独立worker默认CPU执行，经典基线无需Torch。

## 类型契约与生成文件

数据目录、序列、模型注册表、作业状态和预测结果主链使用 Pydantic `response_model` 声明并校验响应；PNG资产使用独立的二进制响应。实际 FastAPI schema 由 [导出脚本](../../scripts/export_openapi.py) 保存为 [openapi.json](openapi.json)，前端 [生成脚本](../../frontend/scripts/api-types.mjs) 使用 openapi-typescript 7.13 与 TypeScript 5.9.3 生成 [api.d.ts](../../frontend/src/generated/api.d.ts)。不要手改生成文件，也不要仅修改前端类型而遗漏后端模型。

变更请求或响应契约后按顺序执行：

```powershell
uv run --locked python scripts/export_openapi.py
pnpm --dir frontend api:generate
uv run --locked python scripts/export_openapi.py --check
pnpm --dir frontend api:check
```

Python CI 检查导出快照是否与当前应用一致；前端 CI 检查生成类型是否与已提交的快照一致。任一侧过期都会失败。该检查确认类型产物同步，不替代真实数据、PNG资产或作业恢复验收。

## 路由与元数据

| GET路由 | 内容 |
|---|---|
| `/api/v1/health` | 服务状态、真实本地数据可用性、模型状态、5秒TTL worker心跳 |
| `/api/v1/datasets` | 已登记的数据源，包括尚未本地取得的候选源 |
| `/api/v1/datasets/{dataset_id}` | 单个数据源的真实来源、许可、计数及本地状态 |
| `/api/v1/sequences?dataset_id=...` | 指定数据源的序列；默认主数据源 |
| `/api/v1/sequences/{sequence_id}` | 序列元数据与连续帧列表、QC状态、显示处理说明 |
| `/api/v1/sequences/{sequence_id}/frames/{frame_index}?layer=...` | PNG显示图层；零起始帧索引 |

主数据源ID为 `drosophila_wound_zenodo_7660424`。序列ID来自公开审计摘要白名单，例如 `WH01`、`WHu01`、`Test01`，不接受任意文件路径。

所有业务JSON响应（含错误）统一包含 `schema_version:"1"`、`provenance`、`dataset_id`、`model_id`、`run_id`、`created_at_utc`。没有模型身份的读取接口对应字段为null。时间字段是本次响应生成的UTC时间，不是实验采集时间。健康和来源目录metadata的provenance为null；数据源列表dataset_id为null，单数据源详情为对应ID；序列列表/详情为对应dataset_id与 `REAL_OBSERVED`。错误中无法确认的来源字段为null。列表保留 `items:[...]`，详情保留现有顶层字段。

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

错误在公共JSON信封内保留 `error:{code,message,details,trace_id}`。非法序列/帧为404，非法图层或类型为422，不支持的方法为405。服务器不回显异常中的本机路径或输入内容。仅支持本地受控使用，没有鉴权或公开部署保证。

## 作业与研究路由

| Method / path | 内容 |
|---|---|
| GET `/api/v1/models` | 六种方法、训练与可用状态、validation所选seed/hash |
| POST `/api/v1/experiments/predict` | 严格请求校验后202入队，不在route内计算 |
| GET `/api/v1/jobs/{id}` | 任务状态、原始请求、取消标记与安全错误 |
| GET `/api/v1/jobs/{id}/result` | 成功结果；尚未成功409 |
| GET `/api/v1/jobs/{id}/frames/{lead}?layer=prediction\|target\|error` | 64×64 PNG；lead为1–24且必须存在于结果中；无有效目标时target/error不可用 |
| POST `/api/v1/jobs/{id}/cancel` | queued立即取消；running协作取消 |
| GET `/api/v1/experiments` | 最近100个持久化任务 |
| GET `/api/v1/experiments/{id}` | 单个持久化实验详情，与作业状态使用同一契约 |
| GET `/api/v1/research` | 已公开冻结test报告，缺失时pending，不计算假分数 |
| GET `/api/v1/research/figures/{name}` | 公开报告白名单内的固定PNG文件名；按报告SHA256核验内容 |

请求例：`{dataset_id:"drosophila_wound_zenodo_7660424",sequence_id:"WH01",model_id:"nca",observation_start:0,observations:4,horizon:24}`。
L仅2/4/8、H1–24，完整范围在源序列内，历史QC有效。没有可选服务器路径或任意权重参数。
结果含逐lead原帧索引、64工作网格 `contours`、`region_area`、`target_area`、七项 `metrics`、
`images:{prediction,target,error}`、来源hash与选中seed/权重hash。每个图像资产仅含 `url` 和 `sha256`；JSON不再返回 `region` 或 `target_region` 像素数组。未来派生目标无效时，`target_area`、`metrics`、`images.target` 与 `images.error` 均为null，但预测仍可生成。图像端点逐次核验对应PNG的SHA256，以ETag返回同一摘要；损坏资产不会作为有效结果静默返回。

全部预测JSON（包括经典基线）统一 `provenance:"MODEL_PREDICTION"`，目标仍为 `target_provenance:"DERIVED_ANNOTATION"`；界面图例显示 `PREDICTION`。预测PNG、目标PNG与误差PNG的 `X-Provenance` 分别为 `MODEL_PREDICTION`、`DERIVED_ANNOTATION`、`PREDICTION_ERROR`，工作网格标记为64×64；原始灰度影像始终是OBSERVED。

结果的 `implementation` 可选，旧历史记录可以为null。新任务记录执行代码的Git SHA、dirty状态、源码hash与环境，并在API入队和worker执行之间核对身份；它与模型权重hash、数据hash分别保留。修改实现文件后应重启API和worker，避免运行中的旧进程与磁盘文件混用。

Research图像只接受无目录部分、以 `forecast-test-` 开头且以 `.png` 结尾的文件名，并且必须出现在公开报告的 `published_figures_sha256` 白名单中。文件读取后再次核验hash；未知文件返回404，缺失或不匹配的白名单资产返回安全错误，不开放任意目录浏览。
完整生命周期与恢复行为见[预测作业架构](prediction-jobs.md)。

## 检查边界

`uv run pytest -q backend/tests` 使用临时合成TIFF/ZIP验证读取、PNG、错误、校验失效、LRU、索引、划分与QC；这些fixture不属于科研数据。真实数据还需单独执行API与界面验收，不能把TestClient或HTTP200当端到端验收。
