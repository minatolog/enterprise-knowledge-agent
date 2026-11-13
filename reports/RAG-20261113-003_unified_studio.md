# 统一 React 工作台交付

日期 2026-11-13；任务 RAG-20261113-003。状态 REVIEW，待用户视觉验收；未提交。

## 实际交付

- 独立 `frontend/` React + TypeScript + React Flow 应用，Vite 构建，lucide 图标。问答/知识库/工作流/运行记录共用 Shell、CSS token、按钮、标题、状态和详情侧栏，无跳转独立旧站点。
- 问答与流程测试共用 Top K/问题/结果状态。真实 query/documents/health API；文本通过 React 转义，不将答案注入 HTML；外链限制 http/https。
- 文档名称搜索、索引元数据详情；运行记录仅当前页面内存；布局仅保存坐标。没有虚构文档数据或指标。
- FastAPI 新增构建目录 mount、首页自动选择构建版或旧版、`/legacy` 回退。API 契约与检索图不改；未接企业运行时认证与数据接口。
- `start-studio.command` 一键安装缺失前端依赖、构建、启动本地服务；`frontend/README.md` 和根 README 有使用说明。新依赖仅 Node 前端，未改 Python 依赖。
- 旧 app/web 页面与既有未提交成果保留。此次根首页变化经过测试，旧 UI 兼容测试改为请求 /legacy。

## 验证

| 验证 | 本次结果 |
|---|---|
| `npm install --prefix frontend --no-audit --no-fund` | 成功，lock 固定解析版本 |
| `npm run build --prefix frontend` | TypeScript strict 检查和 Vite 构建通过；最终 JS 439.71 kB，gzip 141.10 kB，CSS 40.88 kB |
| `python -m unittest discover -s tests -p test_studio.py` | 2 项通过，覆盖构建资源与缺构建回退、404/health/legacy |
| `python -m unittest discover -s tests -p test_app.py` | 32 项通过；生成等仍为测试替身 |
| `zsh -n start-studio.command`、`git diff --check` | 通过；未实际双击脚本，手动执行了等价构建与启动 |
| agent Python 启动 `uvicorn app.api:app --host 127.0.0.1 --port 8021` | 成功，root 与 /studio 均 HTTP 200 |
| 文档接口 | 实时返回 7 文档 / 194 Chunk，只读获取 |
| 浏览器主要交互 | 四页切换、布局保存、搜索 audit、选中文档详情和官方来源链接可用；无 console error/warn |
| 真实问答 | 从新前端发送“审计委员会的主要职责是什么？”，请求 `a4d07879bb094d28813c65ebd13ebe19`，API 成功；2 条来源指向 audit_committee.pdf 第 1/3 页；检索 13422.3 ms、LLM 6547.8 ms、总计 19982.3 ms；运行记录共享同一请求 |
| 响应式 | 默认内置浏览器与临时窄屏检查，未发现水平溢出；实际窄屏页面读取宽度 300 px。随后清除视口覆盖。未系统测试所有浏览器/设备 |

构建警告：React Flow 的 `use client` 被 Vite 客户端构建忽略，构建成功；本应用不使用 SSR。未执行 npm 安全审计或完整 Python/enterprise 回归，未修改相关服务逻辑。

## 界面证据

- [问答页](studio-ui/chat.png)
- [工作流页](studio-ui/workflow.png)

## 限制与后续

1. 固定图可视化；未新增任意流程编译、节点事件 SSE、服务端布局/版本管理、多 Agent。不能把视觉拖动当作执行变更。
2. 刷新清空问答与运行记录；每次问题仍独立，不把聊天列表误称为后端多轮记忆。
3. 文档页只读元数据，未新增上传或原文 Chunk 预览；生产权限不在本轮范围。
4. 答案纯文本安全显示，未引入 Markdown 渲染；资料来源卡不自行分配与正文引用号可能不一致的序号，API 当前没有 source citation_number 字段。
5. 本轮真实生成证明通路，不是答案正确性评测；发现既有 llm.py 系统提示词同时要求专业语气和“鲸鱼娘”口吻，属于既有后端配置，本轮未擅改，详见 ISSUE-01。
6. 本地 dist/node_modules 不跟踪，换机按说明 npm ci/build；生产主入口需在构建后重启 FastAPI。
7. 一键启动复用现有 Python 环境；未实现自动守护进程，关闭终端服务停止。

[执行记录](../docs/ai_workflow/execution_logs/RAG-20261113-003.md) · [前端说明](../frontend/README.md) · [决策](../docs/ai_workflow/decisions/RAG-20261113-003-DECISION-01.md)
