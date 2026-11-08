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
