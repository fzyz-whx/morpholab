# M1 组件清单

| 组件/区域 | 数据与行为 | 状态与可访问性 |
|---|---|---|
| AppShell | 品牌、导航、当前模块；页面路由 | 活动页aria-current，跳到正文入口，窄屏重排 |
| QueryState | metadata请求状态 | 加载status、错误alert与重试、空状态 |
| SourceDetails | API来源、DOI、许可、生物域 | 外链明确，未知字段写未核实 |
| DatasetArchive | 来源选择、序列搜索、本项目split筛选、表格 | API实数、无本地文件禁入序列视图、无匹配可清筛选 |
| SequenceNavigator | 当前数据源全部序列导航 | 真实序列、活动项及项目split；换序列重置播放 |
| LayerControl | observed / annotation / overlay | 原生button pressed；原注释不冒充区域mask |
| ScientificCanvas | 真实PNG、默认按容器宽高完整适配，缩放滑条可手动放大、滚动与“适合画布”复位 | ResizeObserver跟随布局、保持源比例、loading/error、可聚焦键盘区域、img替代文字、源尺寸标识 |
| Timeline | 单帧步进、首尾、播放/暂停、range选择 | frame零基编号，边界禁用，方向键、Home、End，QC标记 |
| FrameInspector | 当前帧QC、触边、项目划分及官方划分 | 文字与颜色共同标识；失败帧仍可访问 |
| ModelState | 未训练/未评估说明 | 无预测执行假按钮，说明下一阶段闸门 |
| ProtocolPage | Research与Methods说明 | 原始/派生标签边界、split局限、原文来源链接 |

M1不含训练控制、指标曲线、模型比较或虚拟干预。实现后的单元/组件测试覆盖请求失败与恢复、筛选/空状态、时间轴边界、图层及播放行为；真实浏览器/E2E由主代理另验收。

Studio主要操作、QC与来源正文至少12px，辅助图例与技术索引至少10px；720px高桌面两侧栏独立滚动。组件测试通过模拟容器测量核验适配、布局变化、手动缩放保持、复位与非正方形比例；真实图像边界与滚动可达性仍需浏览器验收。
