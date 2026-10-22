# 系统分层与运行入口

MorphoLab是本地单用户科研软件。主域、目标和限制由[ADR-0001](../project/decisions/ADR-0001-observed-domain-target-and-split.md)冻结，工程选型见[ADR-0005](../project/decisions/ADR-0005-small-local-stack-and-generated-contracts.md)。

| 层 | 实际职责 | 主要位置 |
|---|---|---|
| 来源与审计 | 安全下载、checksum、ZIP/TIFF解析、逐帧QC与未知项 | scripts/download_data.py / audit_data.py |
| 数据与计算 | 派生区域/SDF、分组窗口、经典方法、模型、训练、指标 | ml/morpholab_ml |
| 研究运行 | 固定预算、来源hash、多seed、失败案例、可复算报告 | scripts/train_matrix.py / evaluate_models.py / report_forecasts.py |
| 本地服务 | 受控注册表、响应schema、持久状态与图像资产 | backend/app |
| 独立worker | 单锁、原子认领、安全模型加载、CPU推理、协作取消 | backend/app/worker.py |
| 科学画布 | 原图/注释/预测/误差、时间轴、坐标、曲线、追溯 | frontend/src |

纯计算包不导入HTTP、界面或数据库。API只校验与入队，训练从CLI执行；PNG编码是已计算区域的显示转换，不在route内执行模型训练。
旧本地作业的区域数组可在读取时补成有hash的显示缓存，API仍只返回图像URL与contour/指标，不把整块像素塞进JSON。

`scripts/serve.py`默认本机8765并监督独立worker。前端构建后由同一服务提供SPA；开发Vite5173代理API。
来源缓存默认artifacts，也可显式指定已核验外部根；任务数据库、结果JSON与PNG只写当前项目artifacts/app。
检查点来自完整固定矩阵，按validation而非test选择；前端不接受任意权重路径或触发训练。

[API合同](api.md)、[持久作业与重启语义](prediction-jobs.md)、[预处理](data-pipeline.md)、[模型](forecast-models.md)分别说明细节。
真实截图与原创模型图见README；[验收记录](../development/acceptance.md)区分fixture、实际进程、浏览器、CPU复算、复训及远端CI。
