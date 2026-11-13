# RAGFlow 风格前端可行性评估

任务：RAG-20261113-001；日期：2026-11-13。依据当前 app/api.py、app/service.py、app/workflow.py、schemas.py，而非历史完成状态推断。

## 结论

现有架构能承载截图风格的节点画布与问答工作台；无需迁移到 RAGFlow，无需更换 Chroma、Embedding 或检索链。截图是视觉参考，不是额外 Agent Prompt 指令。

本次交付为固定 RAG 流程的交互可视化，不是通用低代码 Agent 平台。新增原生 HTML/CSS/JS 三个文件，保留原问答台，不加依赖；通过现有 StaticFiles 路由访问 `/static/workflow.html`。

| 能力 | 当前依据 | 本次范围 |
|---|---|---|
| 暗色画布、节点、曲线、配置侧栏 | 浏览器 HTML/CSS/SVG | 已实现 |
| 节点选择、拖动、缩放、平移 | 前端交互 | 已实现；移动只影响视觉布局 |
| 保存布局 | localStorage | 已实现；仅保存坐标，不保存问题和答案 |
| 真实问答、引用、耗时 | POST /api/v1/query | 已接线；测试含模拟服务，未实测外部模型生成 |
| Top K 调整 | QueryRequest.top_k | 已接线；页面提供 3/5/8 |
| 文档清单 | GET /api/v1/documents | 已接线；索引数量以接口实时返回为准 |
| 节点参数任意编辑 | 后端集中配置，query 不接受模型/Prompt 参数 | 未实现，避免界面伪保存 |
| 任意新增节点、连线并执行 | LangGraph 为固定 StateGraph | 未实现，需安全的流程定义与编译层 |
| 实时节点高亮 / 执行日志 | query 仅最终 JSON，无事件流 | 未实现；目前只显示请求状态和最终耗时 |
| 流程版本、持久保存、多人协作 | 无流程 CRUD/版本/身份接口 | 未实现 |
| 多 Agent / 工具调用 | 当前只有检索生成图 | 未实现，需业务确认后扩展 |

## 架构适配建议

1. 当前阶段：保持 FastAPI 同源提供页面，以 Top K、问答、引用、文档清单形成可演示工作台。本次即此范围，符合总指导 P0 本地 Demo。
2. 下一阶段若需要观测：增加 workflow 元数据只读接口和 SSE 事件；从实际图执行发出事件，不能用计时动画伪装实时轨迹。会话日志涉及问题/证据内容，应按隐私与保留策略设计。
3. 真正可编辑编排：先定义 workflow JSON schema、节点类型白名单、边验证、循环/资源上限、版本与错误契约，再由后端构建 LangGraph。任意代码/工具节点不应直接从客户端执行。保存布局与发布运行版本应分开。
4. React/TypeScript + React Flow 可作为未来复杂编辑器的候选，但本次无须增加 Node 构建链。若决定加入，另立任务评估版本、维护与测试成本。
5. 多 Agent、SSO/ACL、上传入库、生产部署各自立项，不把这些列为“漂亮界面”的前置条件。

## 运行

现有可用环境：

```sh
/opt/anaconda3/envs/agent/bin/python -m uvicorn app.api:app --host 127.0.0.1 --port 8020
```

打开 http://127.0.0.1:8020/static/workflow.html 。原问答页在 `/`。

## 验证与限制

- `node --check app/web/workflow.js` 通过。
- agent 环境执行 `python -m unittest discover -s tests -p test_app.py`：32 项通过；覆盖现有 API/服务契约，生成采用测试替身，不代表真实 DeepSeek 生成验收。
- 本地服务 health 与新页面均 HTTP 200；浏览器确认节点、配置侧栏、API 已连接和布局保存提示。
- 初始尝试系统 Python 缺 fastapi；旧 `/tmp/cnooc_clean_venv` 缺 langgraph/langchain_core，测试和启动失败。复用现有 agent 环境后成功，未安装或修改依赖。
- 本次不重建索引、不修改生产数据、不调用付费模型；未执行完整检索评测、移动端浏览器验收或多用户测试。
- 当前界面节点清单是固定图的展示映射，后端图变化时需要同步维护；retrieve 内部的 Dense/BM25/RRF/Reranker 聚合为一个节点。候选为空不等于完整业务拒答判断。

参考：[RAGFlow 官方仓库](https://github.com/infiniflow/ragflow#-what-is-ragflow)。本次借鉴交互布局，未复制其代码或引入其服务栈。
