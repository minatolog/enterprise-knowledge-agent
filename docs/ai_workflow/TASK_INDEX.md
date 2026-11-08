# AI 任务索引

Task ID 全局唯一；状态含义、编号和 Commit 回填方法见 [制度正文](README.md)。此表只保留检索入口，详细事实在 Prompt 和执行记录中。历史项目任务未取得原始 Prompt，尚未反向登记为“完整 AI 任务”。

| Task ID | 任务名称 | 类型 | 执行模型 | 状态 | Commit | Prompt / 执行记录 |
|---|---|---|---|---|---|---|
| `RAG-20261107-001` | 建立 AI 辅助开发管理与版本追溯制度；用户确认总架构指导 | architecture | Codex（具体模型版本未知） | REVIEW | 未提交；本次任务禁止自动 Commit | [原始及补充指令](prompts/architecture/RAG-20261107-001_ai_dev_governance.md) / [执行记录](execution_logs/RAG-20261107-001.md) / [决策 01](decisions/RAG-20261107-001-DECISION-01.md) / [决策 02](decisions/RAG-20261107-001-DECISION-02.md) |
| `RAG-20261107-002` | 审计当前 RAG 架构并提出 P0 优先级（2026-11-08 修订报告） | architecture | GitHub Copilot（DeepSeek V4.1 Flash）；Codex 审阅 | REVIEW | `2bbaa9c`（审计报告与治理文档）；本轮修订未提交；未 Tag | [原始任务 Prompt](prompts/architecture/RAG-20261107-002_current_architecture_audit.md) / [报告修订草稿](prompts/architecture/RAG-20261107-002_audit_report_revision.md) / [修订 Prompt 实际输出](prompts/architecture/RAG-20261107-002_audit_report_revision_sent.md) / [执行记录](execution_logs/RAG-20261107-002.md) / [审计报告](../../reports/RAG-20261107-002_architecture_audit.md) / [Prompt 逐字归档缺口](issues/RAG-20261107-002-ISSUE-01.md) |
| `RAG-20261108-001` | 建立 CNOOC 评测集与可复现检索基线（暂缓，先搭建应用骨架） | evaluation | Codex 编写 Prompt；DeepSeek 尚未执行 | PLANNED | 无；尚未提交 | [已准备但暂不执行的 Prompt](prompts/evaluation/RAG-20261108-001_cnooc_evaluation_baseline.md) / [执行记录](execution_logs/RAG-20261108-001.md) |
| `RAG-20261108-002` | 搭建 CNOOC RAG 最小可运行应用骨架 | implementation | GitHub Copilot（DeepSeek V4.1 Flash）；Codex 审阅修复 | REVIEW | `336fd28`（2026-11-08 核对；记录勘误见执行记录） | [完整任务 Prompt](prompts/implementation/RAG-20261108-002_application_skeleton.md) / [执行记录](execution_logs/RAG-20261108-002.md) / [ISSUE-01](issues/RAG-20261108-002-ISSUE-01.md) |
| `RAG-20261108-003` | 建立本地网页对话测试界面 | implementation | Codex（具体模型版本未知） | REVIEW | 未提交 | [用户原始消息](prompts/implementation/RAG-20261108-003_local_chat_ui.md) / [执行记录](execution_logs/RAG-20261108-003.md) |
