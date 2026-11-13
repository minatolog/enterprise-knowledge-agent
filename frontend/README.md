# CNOOC Enterprise Knowledge Assistant

> 当前实现以文末 RAG-20261113-005 章节为准；003/004 章节保留演进记录。

任务 RAG-20261113-003。统一 React / TypeScript / React Flow 前端，四视图共用一套导航、颜色、间距、图标和详情侧栏。对接本地单用户 `app.api:app`，并非 `app.enterprise` 多租户入口。

## 本地运行

在仓库根目录运行 `./start-studio.command`，或双击该文件。默认使用现有 `/opt/anaconda3/envs/agent/bin/python`，可用 `RAG_STUDIO_PYTHON` 指定装好 requirements 的 Python，用 `RAG_STUDIO_PORT` 改端口。需要 Node/npm；脚本不安装 Python 依赖，不构建知识库索引。保持终端开启；端口已占用时先使用现有服务或选择另一个端口。

手工构建：

```sh
npm ci --prefix frontend
npm run build --prefix frontend
python -m uvicorn app.api:app --host 127.0.0.1 --port 8021
```

打开 http://127.0.0.1:8021/studio/ 。构建后根地址 `/` 同样加载新界面。未构建时根地址保持旧页面；旧版问答始终保留在 `/legacy`。首次构建后重启 FastAPI 以注册静态目录。

开发：先在 8020 启动后端，再 `npm run dev --prefix frontend`，访问 Vite 输出的 `/studio/` URL。Vite 将 `/api` 和 `/health` 转发到本地 8020，无须放宽 CORS。生产构建由 FastAPI 同源提供，Node 不参与运行时。

## 功能边界

- 问答：真实 query API、返回片段数量、来源链接、页码与 request_id；纯文本安全渲染，暂不解析 Markdown。
- 知识库：只读文档 API、名称筛选与元数据侧栏；不提供上传、正文片段预览与索引写入。
- 工作流：固定后端图映射、拖动/缩放/平移、坐标本地保存。不能新增/删除节点或改变连线；retrieve 卡片聚合召回、融合与精排。
- 运行记录：仅当前页面打开期间内存数据；不是服务端历史、实时节点 Trace 或持久会话。刷新清空，不将问题与答案写入 localStorage。
- `/health` 只代表 API 存活，索引就绪由文档接口及问答错误表达。
- 统一 CSS token 位于 `src/styles.css`；无远程字体、CDN 或外部运行时脚本。新增依赖仅在前端 lock 中。

参考：[React Flow](https://reactflow.dev/learn)、[Vite](https://vite.dev/guide/)。借鉴产品交互思路，未复制 Dify/Langflow 源码。

## 视觉与动效（RAG-20261113-004）

`src/studio-theme.css` 是在基础布局上使用的统一视觉层：石墨底色、青蓝交互、冰绿证据、珊瑚/琥珀辅助色；CSS 页面入场、列表错峰、悬浮与光晕。工作流使用 SVG animateMotion 展示装饰连线流光，并提供总览/聚焦视角。流光不代表实时节点执行状态。

右上角可关闭动效，偏好只保存为 `studio-motion` 的 on/off；系统 `prefers-reduced-motion` 优先使自定义动效静止。没有引入 Motion/GSAP 等新依赖。真实请求进行中只显示整体等待状态，不模拟阶段进度。

## 当前入口：CNOOC Enterprise Knowledge Assistant（RAG-20261113-005）

本节替代上方003/004版本的界面描述。启动方式与API路径不变。

- 主入口为聊天优先的炭黑界面。侧栏可折叠，小屏改为抽屉；聊天、知识库、工作流、运行记录、设置共用壳体。
- 模块：App.tsx负责布局，hooks/useAssistant.ts负责真实请求/对话状态，state/conversations.ts负责历史校验与日期分组，components/负责展示；api.ts独立维护v1请求。
- 回答使用react-markdown/remark-gfm；支持列表、代码、表格。关闭原始HTML与图片，不加载回答中的外部图片；链接只允许http(s)。支持复制与重新生成（重新POST同一问题）。
- 侧栏历史为实际提问，支持搜索/日期分组。默认仅内存，设置中主动开启才保存到当前浏览器localStorage；关闭后删除该功能存储。最多50对话/每个100轮，问答历史包含问题、回答、来源，非服务器会话，浏览器空间不足会明确提示。
- 来源chip可展开文件/页码/路径/Chunk ID并打开官方原文。技术面板默认收起，显示真实候选数量、耗时、返回的Cross-Encoder分数。分数不是置信度。
- API未提供snippet、BM25/Dense分路列表、RRF排名、重排完整列表、citation_number、原件总页数、分类或更新时间；页面明确标为未提供。不可把索引页码跨度当作PDF真实页数。
- 当前v1无文件上传和服务器历史；企业v2是独立鉴权入口，本轮不混接。
- 工作流继续固定图可视化与本地布局保存，使用懒加载。新样式只引用assistant.css；旧styles.css/studio-theme.css保留为历史文件，不再加载到新入口。
- 测试：`npm test --prefix frontend`（Node 24内置TS支持），构建：`npm run build --prefix frontend`。

视觉参考：[用户指定仓库](https://github.com/bhaktofmahakal/UI-Engineering)。关联Demo当次返回DEPLOYMENT_PAUSED，不能像素级核对；未复制源码或品牌。
