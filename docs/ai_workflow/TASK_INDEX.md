# AI 任务索引

Task ID 全局唯一；状态含义、编号和 Commit 回填方法见 [制度正文](README.md)。此表只保留检索入口，详细事实在 Prompt 和执行记录中。历史项目任务未取得原始 Prompt，尚未反向登记为“完整 AI 任务”。

| Task ID | 任务名称 | 类型 | 执行模型 | 状态 | Commit | Prompt / 执行记录 |
|---|---|---|---|---|---|---|
| `RAG-20261112-001` | 企业级 RAG 参考架构与技术栈图解 | architecture | Codex / GPT-6（具体变体未知） | REVIEW | 未提交 | [用户原文](prompts/architecture/RAG-20261112-001_enterprise_rag_explanation.md) / [执行记录](execution_logs/RAG-20261112-001.md) |
| `RAG-20261107-001` | 建立 AI 辅助开发管理与版本追溯制度；用户确认总架构指导 | architecture | Codex（具体模型版本未知） | REVIEW | 未提交；本次任务禁止自动 Commit | [原始及补充指令](prompts/architecture/RAG-20261107-001_ai_dev_governance.md) / [执行记录](execution_logs/RAG-20261107-001.md) / [决策 01](decisions/RAG-20261107-001-DECISION-01.md) / [决策 02](decisions/RAG-20261107-001-DECISION-02.md) |
| `RAG-20261107-002` | 审计当前 RAG 架构并提出 P0 优先级（2026-11-08 修订报告） | architecture | GitHub Copilot（DeepSeek V4.1 Flash）；Codex 审阅 | REVIEW | `2bbaa9c`（审计报告与治理文档）；本轮修订未提交；未 Tag | [原始任务 Prompt](prompts/architecture/RAG-20261107-002_current_architecture_audit.md) / [报告修订草稿](prompts/architecture/RAG-20261107-002_audit_report_revision.md) / [修订 Prompt 实际输出](prompts/architecture/RAG-20261107-002_audit_report_revision_sent.md) / [执行记录](execution_logs/RAG-20261107-002.md) / [审计报告](../../reports/RAG-20261107-002_architecture_audit.md) / [Prompt 逐字归档缺口](issues/RAG-20261107-002-ISSUE-01.md) |
| `RAG-20261108-001` | 建立 CNOOC 评测集与可复现检索基线（后续并入 P0 任务，不单独执行） | evaluation | Codex 编写 Prompt；未单独派发执行 | PLANNED（未单独执行；由 RAG-20261109-001 承接） | 无；尚未提交 | [已准备但不单独执行的 Prompt](prompts/evaluation/RAG-20261108-001_cnooc_evaluation_baseline.md) / [执行记录](execution_logs/RAG-20261108-001.md) / [承接任务](execution_logs/RAG-20261109-001.md) |
| `RAG-20261108-002` | 搭建 CNOOC RAG 最小可运行应用骨架 | implementation | GitHub Copilot（DeepSeek V4.1 Flash）；Codex 审阅修复 | REVIEW | `336fd28`（2026-11-08 核对；记录勘误见执行记录） | [完整任务 Prompt](prompts/implementation/RAG-20261108-002_application_skeleton.md) / [执行记录](execution_logs/RAG-20261108-002.md) / [ISSUE-01](issues/RAG-20261108-002-ISSUE-01.md) |
| `RAG-20261108-003` | 建立本地网页对话测试界面 | implementation | Codex（具体模型版本未知） | REVIEW | `28ffdd6`（2026-11-09 核对；记录勘误见执行记录） | [用户原始消息](prompts/implementation/RAG-20261108-003_local_chat_ui.md) / [执行记录](execution_logs/RAG-20261108-003.md) |
| `RAG-20261109-001` | 完成 CNOOC RAG 本地项目 P0 验收与交付 | implementation | GitHub Copilot（DeepSeek V4.1 Flash）；Codex / gpt-6.1-sol 验收 | COMPLETED（P0 本地交付验收通过；未提交） | 无；本任务未自动 Commit/Tag/Push | [实际 Prompt](prompts/implementation/RAG-20261109-001_p0_completion.md) / [执行记录](execution_logs/RAG-20261109-001.md) / [Codex 验收](../../reports/p0_codex_acceptance.md) / [真实问答核验](../../reports/p0_real_qa_verification.md) / [检索评测](../../reports/eval/cnooc_retrieval_eval_v1.md) / [干净复现](../../reports/p0_clean_reproduction.md) |

| `RAG-20261112-002` | 接入 LangChain 与 LangGraph | implementation | Codex / GPT-6（具体变体未知） | REVIEW | 未提交 | [用户原文](prompts/implementation/RAG-20261112-002_langchain_langgraph.md) / [执行记录](execution_logs/RAG-20261112-002.md) |

| `RAG-20261112-003` | 企业级 RAG 架构与完成状态图 | architecture | Codex / GPT-6（具体变体未知） | REVIEW | 未提交 | [用户原文](prompts/architecture/RAG-20261112-003_architecture_status.md) / [执行记录](execution_logs/RAG-20261112-003.md) |

| `RAG-20261113-001` | RAGFlow 风格本地工作流界面与可行性评估 | implementation | Codex / GPT-6（具体变体未知） | REVIEW | 未提交 | [用户原文](prompts/implementation/RAG-20261113-001_workflow_ui.md) / [执行记录](execution_logs/RAG-20261113-001.md) |

| `RAG-20261113-002` | 企业 RAG 待办补齐与验收状态图 | implementation | Codex / GPT-6（具体变体未知） | REVIEW（本地通过，外部待验收） | 未提交 | [Prompt](prompts/implementation/RAG-20261113-002_enterprise_completion.md) / [执行](execution_logs/RAG-20261113-002.md) |

| `RAG-20261113-003` | React 统一 RAG 工作台与 React Flow 画布 | implementation | Codex / GPT-6（具体变体未知） | REVIEW | 未提交 | [Prompt](prompts/implementation/RAG-20261113-003_unified_react_ui.md) / [执行](execution_logs/RAG-20261113-003.md) |

| `RAG-20261113-004` | 统一工作台配色、质感与动效升级 | implementation | Codex / GPT-6（具体变体未知） | REVIEW | 未提交 | [Prompt](prompts/implementation/RAG-20261113-004_visual_motion.md) / [执行](execution_logs/RAG-20261113-004.md) |

| `RAG-20261113-005` | Grok-inspired CNOOC 企业知识助手重设计 | implementation | Codex / GPT-6（具体变体未知） | REVIEW | 未提交 | [实际附件](prompts/implementation/RAG-20261113-005_grok_assistant.md) / [执行](execution_logs/RAG-20261113-005.md) |
