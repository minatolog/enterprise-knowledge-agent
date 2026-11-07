# AI 任务索引

Task ID 全局唯一；状态含义、编号和 Commit 回填方法见 [制度正文](README.md)。此表只保留检索入口，详细事实在 Prompt 和执行记录中。历史项目任务未取得原始 Prompt，尚未反向登记为“完整 AI 任务”。

| Task ID | 任务名称 | 类型 | 执行模型 | 状态 | Commit | Prompt / 执行记录 |
|---|---|---|---|---|---|---|
| `RAG-20261107-001` | 建立 AI 辅助开发管理与版本追溯制度；用户确认总架构指导 | architecture | Codex（具体模型版本未知） | REVIEW | 未提交；本次任务禁止自动 Commit | [原始及补充指令](prompts/architecture/RAG-20261107-001_ai_dev_governance.md) / [执行记录](execution_logs/RAG-20261107-001.md) / [决策 01](decisions/RAG-20261107-001-DECISION-01.md) / [决策 02](decisions/RAG-20261107-001-DECISION-02.md) |
| `RAG-20261107-002` | 审计当前 RAG 架构并提出 P0 优先级 | architecture | GitHub Copilot（DeepSeek V4.1 Flash） | REVIEW | 未提交；本次任务禁止 Commit/Tag | [任务 Prompt（拟交付版）](prompts/architecture/RAG-20261107-002_current_architecture_audit.md) / [执行记录](execution_logs/RAG-20261107-002.md) / [审计报告](../../reports/RAG-20261107-002_architecture_audit.md) |
