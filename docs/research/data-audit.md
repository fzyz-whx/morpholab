# 公开数据审计

更新日期：2026-10-21。状态：**M0 进行中，尚未通过数据验收闸门。**

## 网页与元数据证据

主源为 [Zenodo 7660424](https://zenodo.org/records/7660424)，[官方 API](https://zenodo.org/api/records/7660424) 已实际返回 HTTP 200、`access_right: open` 和 `license.id: cc-by-4.0`。元数据列出 `Dataset.zip`、198,715,081 bytes、`md5:5d1506d67b4be24de0304b58d17361cb`。

发布者描述：61 条果蝇胚胎 **in vivo** 激光创面闭合时序，44/12/5 train/validation/test，约每分钟一次，处理后的图像为 128×128；Video 与 Segmentations 两个目录，后者为 skeletonized segmentations。上述数量、尺寸、时间与目录是来源陈述，当前尚未由本地包内容全部核实。

采集、最大投影、配准、裁剪和降采样会改变物理标尺的解释。原文报告的原始标尺不能直接填入处理后样本；当前 `pixel_size_um: null`。生物干预条件、绝对实验时间、实验独立性和发布划分映射待确认。

## 实际下载与内容核验

恢复项目之前曾尝试内存读取全包，未完成即因选题比较暂停而中止，没有缓存文件；那次尝试不作为完整下载证据。恢复后使用可复现工具完成真实下载：

```sh
uv run --locked python scripts/download_data.py
```

默认文件位于 `artifacts/raw/zenodo_7660424/Dataset.zip`，不会进入 Git。首次传输 207.796 秒，一次尝试成功；独立读回完整文件后再次验证：

| 检查 | 实测结果 |
|---|---|
| 字节数 | 198,715,081 |
| 发布 MD5 与本地值 | `5d1506d67b4be24de0304b58d17361cb`，一致 |
| 本地 SHA256 | `0f74010ea3eb5820176c1c04a1804928efe23002dde3c2429e1c90defb497e57` |
| ZIP 目录 | 126 项，2 个目录、124 个 TIFF |
| 解压声明大小 | 358,798,034 bytes |
| 包内额外条款 | 未找到 README / LICENSE 附件；许可依据为官方 API |

**目录级差异：** `Videos/` 与 `Segmentations/` 各 62 个同名 TIFF：WH01–35、WHu01–22、Test01–05。不能把 62 个配对文件直接等同于 62 个有效独立实验；它与网页的 61 条不一致。目录中没有 train/validation 子目录，官方 44/12/5 的映射尚待取得，不从名称自行猜测。

本地证据：`record-api.json`、`download-status.json` 与 `artifacts/audit/archive-inventory.json`。下载器支持 `.part` 续传、有界重试和总体时间预算，只有大小与 MD5 通过后才生成最终文件名。ZIP 本次只列目录及读取有上限的说明文件，逐帧内容验收另行记录。

尚未确认标签是开放骨架、闭合轮廓还是填充区域。不会直接把它当作区域真值计算 Dice/IoU，不会先训练再反向解释标签。

## 次级来源

| 来源 | 已确认层级 | 当前限制 |
|---|---|---|
| [GigaDB 100118](https://gigadb.org/dataset/100118) | [DataCite](https://api.datacite.org/dois/10.5524/100118)记录体外 MDCK/DA3 的31组实验及CC0 1.0 | 原始 Cell Image Library 链接未取得可用数据，原图条目许可未逐项核对；代码GPL不等于图像许可 |
| [BBBC019v2](https://bbbc.broadinstitute.org/BBBC019) | 官方页列 171 张静态图像、人工标注与 CC BY 3.0 | 未下载；无连续时间点配对证据，禁止当视频 |

CC BY 许可要求的署名、来源与修改说明将单独落地；源码 MIT 不覆盖第三方资源。包内条款与附件仍待检查，当前不向公开仓库提交影像。

## M0 数据闸门

- [x] 公开压缩包完整下载且发布 checksum 一致。
- [ ] 至少两条真实连续序列，每条至少六个不同时间点；时间/重复/缺失检查有记录。
- [ ] 本地真实帧预览及标注叠加 QA，人工审视对齐。
- [ ] hash、源 ID、逐序列清单、标签定义、官方划分与限制可追溯。
- [ ] 确认数据域命名准确；未知元数据保留 null。
- [ ] 监督目标、分组与初始指标通过 ADR，不把推导标签冒充原始区域标注。

研究问题与相邻工作也属于 M0 验收，数据可用不自动意味着方法有新颖性。
