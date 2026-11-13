# AI 开发流水账

按日期追加简要事件；完整 Prompt、操作、命令和证据见对应执行记录。历史记录保留在 [原 DevLog](../devlog/) 和 [项目报告](../../reports/)，不在此伪造回填。

| 日期（悉尼） | Task ID | 事件 | 状态 | 详情 |
|---|---|---|---|---|
| 2026-11-07 | `RAG-20261107-001` | 检查现有代码、文档、Git 与本地索引；建立 AI 开发制度和模板。待用户审查；未 Commit/Tag。 | REVIEW | [执行记录](execution_logs/RAG-20261107-001.md) / [基线审计](BASELINE_AUDIT.md) |
| 2026-11-07 | `RAG-20261107-001` | 用户指定其架构指导为全项目总指挥；制度与 `AGENTS.md` 已补充该优先级，原文未改。 | REVIEW | [补充指令](prompts/architecture/RAG-20261107-001_ai_dev_governance.md) / [执行轮次 2](execution_logs/RAG-20261107-001.md) |
| 2026-11-07 | `RAG-20261107-002` | 根据总架构第 15 节准备交给 DeepSeek 的只读架构审计 Prompt；DeepSeek 尚未执行。 | PLANNED | [Prompt](prompts/architecture/RAG-20261107-002_current_architecture_audit.md) / [执行记录](execution_logs/RAG-20261107-002.md) |
| 2026-11-07 | `RAG-20261107-002` | 完成只读架构审计：核实 7 份 PDF/106 页/194 Chunk、Chroma 与 Chunk ID 一致、7 题 Smoke 严格 Reranker Top-1 4/7、Top-3 5/7；产出审计报告与 P0 优先级建议；未运行索引/模型/API。 | REVIEW | [执行记录](execution_logs/RAG-20261107-002.md) / [审计报告](../../reports/RAG-20261107-002_architecture_audit.md) |
| 2026-11-07 | `RAG-20261107-002` | Codex 复核审计报告：主要事实核对通过；记录实际 Prompt 归档缺口和计划验收口径待修正。未改报告或业务代码。 | REVIEW | [审阅记录](execution_logs/RAG-20261107-002.md) / [ISSUE-01](issues/RAG-20261107-002-ISSUE-01.md) |
| 2026-11-07 | `RAG-20261107-002` | 更正上一条：用户确认 Codex 提供的完整 Prompt 已在仓库归档；仅 DeepSeek 执行记录所称的细微差异尚无证据核对。 | REVIEW | [更正记录](execution_logs/RAG-20261107-002.md) / [ISSUE-01](issues/RAG-20261107-002-ISSUE-01.md) |
| 2026-11-07 | `RAG-20261107-002` | 为 DeepSeek 准备架构审计报告修订指令；只规划报告和记录勘误，尚未执行修订。 | REVIEW | [修订 Prompt](prompts/architecture/RAG-20261107-002_audit_report_revision.md) / [执行记录](execution_logs/RAG-20261107-002.md) |
| 2026-11-08 | `RAG-20261107-002` | 完成审计报告修订：核对归档 Prompt 与聊天指令差异、拆分任务 1/3 评测验收、修正引用字段与语义支持表述、明确 Step 0 仅为审计快照；状态仍 REVIEW；未 Commit/Tag。 | REVIEW | [执行记录](execution_logs/RAG-20261107-002.md) / [审计报告](../../reports/RAG-20261107-002_architecture_audit.md) / [ISSUE-01](issues/RAG-20261107-002-ISSUE-01.md) |
| 2026-11-08 | `RAG-20261107-002` | Codex 验收：报告四项技术修订通过；发现原始聊天版 Prompt 仅有差异表、未逐字归档，并补存 Codex 实际输出的修订 Prompt。任务仍 REVIEW。 | REVIEW | [验收记录](execution_logs/RAG-20261107-002.md) / [ISSUE-01](issues/RAG-20261107-002-ISSUE-01.md) |
| 2026-11-08 | `RAG-20261108-001` | 准备交给 DeepSeek 的 CNOOC 评测集与检索基线实施 Prompt；尚未执行评测或修改业务代码。 | PLANNED | [Prompt](prompts/evaluation/RAG-20261108-001_cnooc_evaluation_baseline.md) / [执行记录](execution_logs/RAG-20261108-001.md) |
| 2026-11-08 | `RAG-20261108-001` | 用户质疑在应用骨架缺失时优先做大评测；已核对代码并暂缓该任务，优先规划服务层、API、配置/错误处理和运行闭环。 | PLANNED（暂缓） | [规划更正](execution_logs/RAG-20261108-001.md) |
| 2026-11-08 | `RAG-20261108-002` | 为 DeepSeek 准备最小应用骨架任务：复用现有 CLI 链路，新增服务/API、基础配置与错误处理、测试和运行说明；尚未执行。 | PLANNED | [Prompt](prompts/implementation/RAG-20261108-002_application_skeleton.md) / [执行记录](execution_logs/RAG-20261108-002.md) |
| 2026-11-08 | `RAG-20261108-002` | 完成最小应用骨架：共享 `RAGService`、FastAPI 三端点、配置/日志/错误、README/.env.example、30 个 mock 测试；health/documents 实测通过，真实 DeepSeek 未验证；状态 REVIEW；未 Commit/Tag。 | REVIEW | [执行记录](execution_logs/RAG-20261108-002.md) / [README](../../README.md) |
| 2026-11-08 | `RAG-20261108-002` | Codex 验收并修复 `.env` 加载顺序和布尔型 Top-K 校验；31 个应用测试及 8 个旧测试通过，health/documents 独立实测，真实 DeepSeek 问答仍未验证。 | REVIEW | [验收记录](execution_logs/RAG-20261108-002.md) / [ISSUE-01](issues/RAG-20261108-002-ISSUE-01.md) |
| 2026-11-08 | `RAG-20261108-003` | 新增 FastAPI 同源本地问答页面，可连续提问并查看来源/页码、索引状态；32 个应用测试通过，首页与静态资源 HTTP 实测通过，真实提问与浏览器视觉体验待验收。发现并补记 `RAG-20261108-002` 已提交的追溯信息。 | REVIEW | [执行记录](execution_logs/RAG-20261108-003.md) / [Prompt](prompts/implementation/RAG-20261108-003_local_chat_ui.md) |
| 2026-11-09 | `RAG-20261109-001` | 为 DeepSeek 起草剩余 P0 的直接执行 Prompt，覆盖真实问答、可信评测、引用核查和交付复现；尚未执行。旧评测规划任务仅作参考，并补记网页任务的已提交 SHA。 | PLANNED | [拟发送 Prompt](prompts/implementation/RAG-20261109-001_p0_completion.md) / [执行记录](execution_logs/RAG-20261109-001.md) |
| 2026-11-09 | `RAG-20261109-001` | 完成 P0 本地交付：4 次真实 DeepSeek 问答与来源核验；31 题评测集（26 有答案+5 无答案）和四路检索对照；修复企业问答人设 Prompt；README/演示/测试补齐；干净 venv 复现 7 文档/194 Chunk、API 与 46 个测试全部通过。未自动 Commit/Tag。 | COMPLETED（待用户审查） | [执行记录](execution_logs/RAG-20261109-001.md) / [真实问答核验](../../reports/p0_real_qa_verification.md) / [评测报告](../../reports/eval/cnooc_retrieval_eval_v1.md) / [干净复现](../../reports/p0_clean_reproduction.md) |
| 2026-11-09 | `RAG-20261109-001` | Codex 独立验收通过：完整 46 项测试与四路 31 题排序复现一致；补测网页默认配置、核对资料/索引哈希并修正文档说明。保持 AI 标签、有限真实问答及未测浏览器交互的边界；未提交。 | COMPLETED | [独立验收](../../reports/p0_codex_acceptance.md) / [执行记录](execution_logs/RAG-20261109-001.md) |
| 2026-11-09 | `RAG-20261109-001` | 按用户新指令恢复原有可爱口吻和安慰员工指令，保留事实/引用要求；32 项应用测试通过，未追加真实 API 调用。 | COMPLETED | [用户指令](prompts/debugging/RAG-20261109-001_restore_cute_tone.md) / [执行记录](execution_logs/RAG-20261109-001.md) |
| 2026-11-09 | `RAG-20261109-001` | 按用户要求重启 127.0.0.1:8767 的问答服务，首页/健康/文档接口均 200，索引仍为 7/194；未调用 DeepSeek。 | COMPLETED | [执行记录](execution_logs/RAG-20261109-001.md) |

| 2026-11-12 | `RAG-20261112-001` | 企业级 RAG 参考架构、技术栈与流程图讲解；官方资料核对及当前代码只读检查，不实施迁移。 | REVIEW | [执行记录](execution_logs/RAG-20261112-001.md) / [用户原文](prompts/architecture/RAG-20261112-001_enterprise_rag_explanation.md) |

| 2026-11-12 | `RAG-20261112-002` | LangChain 核心接口与 LangGraph 默认问答编排接入；51 项测试通过，隔离索引真实检索及 API 集成通过，生成使用模拟函数。 | REVIEW | [执行记录](execution_logs/RAG-20261112-002.md) / [决策](decisions/RAG-20261112-002-DECISION-01.md) / [问题修复](issues/RAG-20261112-002-ISSUE-01.md) |

| 2026-11-12 | `RAG-20261112-003` | 企业级 RAG 绿红完成状态图与技术应用表，拆分本地实现和生产待办。 | REVIEW | [报告](../../reports/RAG-20261112-003_architecture_status.md) / [执行记录](execution_logs/RAG-20261112-003.md) |

- 2026-11-13 · `RAG-20261113-001` · Codex / GPT-6（具体变体未知）：新增独立 RAGFlow 风格固定流程工作台、可行性评估；复用现有 API，无新依赖；API/服务测试 32 项通过，本地页面 HTTP 200、浏览器显示通过，未复测外部生成。状态 REVIEW，未提交。[执行记录](execution_logs/RAG-20261113-001.md) / [评估](../../reports/RAG-20261113-001_workflow_ui_assessment.md)。

| 2026-11-13 | `RAG-20261113-002` | 企业扩展：权限/版本/队列/快照/上下文/会话/核验/运维工具；70项测试、真实队列缓存/OCR/恢复及1题真实生成核验通过；Docker完整部署和企业联调待验收。 | REVIEW | [交付](../../reports/RAG-20261113-002_delivery.md) / [执行](execution_logs/RAG-20261113-002.md) |

- 2026-11-13 · `RAG-20261113-003` · Codex / GPT-6（具体变体未知）：统一 React/TypeScript/React Flow 四视图工作台；34项相关测试与类型构建通过，真实问答及来源/耗时已浏览器核验；一键启动脚本与旧页回退保留。状态 REVIEW，未提交。[执行记录](execution_logs/RAG-20261113-003.md) / [报告](../../reports/RAG-20261113-003_unified_studio.md)。

- 2026-11-13 · `RAG-20261113-004` · Codex / GPT-6（具体变体未知）：统一石墨/青蓝/冰绿/珊瑚视觉层，新增页面与悬浮动效、SVG装饰流光、动效开关、聚焦/总览；类型构建与浏览器动效切换/窄屏检查通过，无新依赖/后端改动。状态 REVIEW，未提交。[执行记录](execution_logs/RAG-20261113-004.md)。

- 2026-11-13 · `RAG-20261113-005` · Codex / GPT-6（具体变体未知）：Grok-inspired聊天优先重设计，模块化状态/API/组件，安全Markdown、真实来源/技术详情、可选浏览器历史、移动抽屉与设置；40项相关测试及构建通过，两次真实模型问答与浏览器保存/恢复核验。状态REVIEW，未提交。[执行](execution_logs/RAG-20261113-005.md) / [交付](../../reports/RAG-20261113-005_assistant_delivery.md)。
