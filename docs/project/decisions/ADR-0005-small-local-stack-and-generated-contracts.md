# ADR-0005 · 本地科研版本的轻量依赖与生成契约

- 日期：2026-10-22
- 状态：实现后补充记录的工程选型，不冒称训练前预注册
- 范围：总任务书默认技术栈的具体落地，不改变研究域、监督目标、模型或实验预算

## 选择

保留React/TypeScript/Vite/Tailwind、TanStack Query、FastAPI/Pydantic、SQLAlchemy/SQLite、独立worker、PyTorch/NumPy/SciPy与uv/pnpm锁文件。
本地交互用React state和语义化原生控件，不引入Zustand或Radix/shadcn；当前会话状态局限于单工作台，持久实验由后端队列保存。
SVG足以表达轮廓、误差资产叠加和实际曲线，未引入按需选项ECharts；现有单元与真实键鼠检查覆盖交互与可读性。
轮廓QC/EDT由SciPy执行，图像编码用Pillow，等值线用contourpy；没有为重复能力添加OpenCV/scikit-image的大型二进制依赖。

替代方案是完整引入默认组件/状态/图表栈；当前没有相应复杂度需求，反而增加维护与打包边界。若后续跨页编辑会话复杂化、可访问控件缺口或曲线规模增加，再基于实际问题扩展依赖。

## 契约与包管理

最终审查发现早期手写DTO不足以防字段漂移，补齐数据浏览与预测主链Pydantic响应模型。
FastAPI导出实际OpenAPI快照，openapi-typescript生成前端声明；CI分别拒绝过期快照和过期TS类型。
TypeScript锁到5.9.3，满足生成器7.13.0声明的peer范围；不是修改全局编译器。
客户端类型是静态保证，不冒称客户端进行了运行时JSON校验；服务器严格验证响应和请求，真实E2E验证整条链。

Python采用仓库根单一uv项目，将纯计算包放在`ml/morpholab_ml`；backend/scripts从源码树运行。
不制造没有独立分发用途的多个pyproject、空control目录或无用途配置文件。当前只有进程环境变量配置缓存根，未引入自动读取.env的隐式行为。

后果：依赖更小、边界直接，同时必须维护生成器与OpenAPI快照。语义控件的键盘/错误反馈仍需实际验证，不能因减少库而省略。
