# AI 辅助开发与版本追溯制度

项目的**总开发架构和阶段路线**由用户编写的 [《企业级 RAG 项目架构与开发指导》](../enterprise_rag_architecture_development_guide.md) 指挥。本目录只规定**如何记录与追溯** AI 协作：保存实际收到的任务指令、执行结果、决策和问题排查，不另立技术路线。每次任务先读总指导，再核对当前代码；指导中的目标不等于当前已实现功能，出现差异应记入任务记录。原有 `docs/devlog/` 和 `reports/` 保持原样。

## 每次新任务怎么做

1. 检查 `git status`、[任务索引](TASK_INDEX.md)、相关代码和文档。按澳大利亚悉尼本地日期取 `RAG-YYYYMMDD-NNN`；`NNN` 为该日未使用的下一个三位编号。先在整个 `docs/ai_workflow/` 中搜索 ID，防止多工具碰撞。同一任务换工具、重试或分次执行仍沿用原 ID，并在执行记录中追加一次运行。
2. 把实际收到的**完整 Prompt**原样存入 `prompts/<类型>/RAG-YYYYMMDD-NNN_简短名称.md`。类型为 `architecture`、`implementation`、`debugging`、`evaluation` 或 `optimization`；无法归类的管理任务使用 `architecture`。同时写明接收日期、来源工具、记录范围、附件位置及有无脱敏。附件本身不在仓库时不能声称已归档附件全文。
3. 在 `TASK_INDEX.md` 登记并创建 `execution_logs/<Task ID>.md`。先填目标、范围、验收条件；执行后追加本次运行的文件、命令、结果、问题和状态。任何 AI 工具都应读这两个文件，不依赖别的聊天窗口。
4. 重要选择用 `decisions/<Task ID>-DECISION-01.md` 记录候选方案与原因；Bug 用 `issues/<Task ID>-ISSUE-01.md` 记录复现、排查和验证。必要时建立 `milestones/<Task ID>-MILESTONE-01.md`。编号在同一 Task ID 内递增。
5. 更新索引、[开发流水账](DEVELOPMENT_LOG.md)和本次执行记录。`PLANNED` 表示待执行，`IN_PROGRESS` 表示执行中，`REVIEW` 表示实施完成待验收/提交，`COMPLETED` 表示约定验收已通过，`BLOCKED` 表示阻塞并写明原因。失败或中止也必须留痕。

模板只供复制，不是事实记录。实际证据优先于模板字段；未知写“未知/未运行/待确认”，不要填猜测值。历史任务若缺原始 Prompt，只能建**范围明确的历史索引**并链接可核验的 Git Commit、旧日志和报告，不能倒推并伪造完整 Prompt。

## Git 与任务如何关联

- 一个独立任务原则上对应一个任务 Commit；Commit 标题含 Task ID，例如 `docs(RAG-20261107-001): establish AI development records`。提交前检查 `git status --short`、`git diff`、`git diff --cached` 和所有新文件，确保没有密钥、原始 PDF、数据库或别人的未提交修改。Prompt 与执行记录在同一任务 Commit 中，Commit 正文可加 `Prompt: docs/...`、`Execution: docs/...`、`Decision: docs/...`。
- 创建 Commit 前不知道它自己的 SHA，执行记录先写“待提交”。创建后把任务 Commit 的完整 SHA 回填到执行记录和索引，并用一次小的追溯更新 Commit 保存；不需要把追溯更新 Commit 的自身 SHA 再写回自身。也可用 `git log --all --grep='RAG-YYYYMMDD-NNN'` 查找任务提交。
- Tag 只在里程碑验收通过、指向已存在的稳定 Commit 后创建。记录 Tag、目标完整 SHA、验收证据与日期；例如 `v0.2.0-retrieval-evaluation` 是格式示例，不代表当前存在。执行 Commit、Tag 或 Push 必须符合当前任务的授权。初始化任务 `RAG-20261107-001` 明确**不创建 Commit 或 Tag**。
- 查看旧版：先 `git status`，再 `git log --oneline --decorate`、`git tag --list`、`git show <commit>:<path>`。要试运行旧版，使用 `git switch -c restore/<名称> <tag-or-commit>` 建独立分支；共享分支要撤销已发布提交时，先核对影响，再考虑 `git revert <commit>`。避免用 `reset --hard` 或 `clean -fd` 作为常规恢复方式。
- Git 只能恢复已跟踪并提交的内容。当前仓库忽略的 PDF、`.env`、ChromaDB 和 `.index_state` 不会因切换 Commit/Tag 自动恢复；另行保留其来源、校验与安全备份。

## 目录与责任

| 路径 | 用途 |
|---|---|
| `prompts/{architecture,implementation,debugging,evaluation,optimization}/` | 每项任务实际收到的完整指令及来源说明 |
| `execution_logs/` | 同一 Task ID 下按次追加的真实执行、命令、测试与 Git 记录 |
| `decisions/` | 重要技术选择、备选方案、证据和重新评估条件 |
| `issues/` | Bug 复现、排查、修复与验证 |
| `milestones/` | 经确认的重要阶段、相关任务、Commit 和 Tag |
| `templates/` | 五类空白模板；复制后填真实内容 |
| `TASK_INDEX.md` | Task ID、Prompt、执行状态和 Commit 的入口 |
| `DEVELOPMENT_LOG.md` | 只追加的时间线，链接详细记录 |
| `BASELINE_AUDIT.md` | 制度建立时的只读检查和文档差异 |

内部链接用相对路径。完成记录原则上只追加；确需修正时，在原文件末尾注明更正日期、原因、旧值和新值。Prompt 原文不编辑，更正请加勘误或后续 Prompt。避免把同一份执行细节复制到多个文件：索引和流水账只写链接及一句话状态。

## 跨 AI 工具交接

- **ChatGPT/负责人：**创建 Task ID、审查代码与文档事实、制定验收条件、归档实际交给执行工具的 Prompt。若网页端不能写仓库，先把完整指令交给执行工具并要求其在动代码前保存。
- **Codex/DeepSeek：**先读总架构指导，再打开 Task ID 对应的 Prompt、执行记录和 Git 状态；按当前阶段和授权范围执行，记录工具/模型、结果和实际测试。换工具时继续同一 Task ID，追加新的执行轮次。
- **负责人验收：**核对 Diff、测试证据和风险，再决定是否提交、打 Tag 或继续修改。任何工具都不能用聊天记忆代替仓库记录。

入门参见五份[模板](templates/TASK_PROMPT_TEMPLATE.md)和本次[实际任务记录](execution_logs/RAG-20261107-001.md)。
