<!--
Task ID: RAG-20261107-001
接收日期: 2026-11-07 (Australia/Sydney)
来源: 用户在 Codex 对话中补发的完整任务说明
记录范围: 下方保留补发消息的完整可见原文。首次投递在“### 1. pro”处截断，随后用户补发完整任务；没有附件或敏感内容被省略。
执行记录: ../../execution_logs/RAG-20261107-001.md
-->

[执行记录](../../execution_logs/RAG-20261107-001.md)

# Task: 为 enterprise-knowledge-agent 建立 AI 辅助开发管理与版本追溯制度

你现在负责为 `enterprise-knowledge-agent` 项目建立一套长期、规范、可维护的 AI 辅助开发管理制度。

这次任务的核心不是开发新的 RAG 功能，而是完善项目的工程管理体系，使 ChatGPT、Codex、DeepSeek 等不同 AI 工具能够围绕同一套项目规范协作。

## 一、项目背景

这是一个基于企业官方资料构建的 RAG 知识问答系统。

目前已经实现或规划的主要技术流程包括：

1. PDF 逐页解析与文本切块。
2. Embedding 向量化及 ChromaDB 存储。
3. BM25 关键词检索。
4. Hybrid Retrieval 混合检索。
5. RRF 检索结果融合。
6. Cross-Encoder Reranker 重排序。
7. DeepSeek API 答案生成。
8. 回答附带来源文件路径和 PDF 页码。
9. SHA-256 文件哈希与增量索引。
10. 检索评测与优化。

当前知识库使用 CNOOC 官方资料，生产 Collection 为 `cnooc_knowledge`。

此前同步的历史状态为：7 份正式索引文件、106 页、194 个 Chunk。具体数量和当前实现必须以实际仓库检查结果为准，不要直接将历史数据视为当前状态。

项目已经经历了多轮开发和优化，因此需要建立正式的开发记录制度。

## 二、本次任务目标

建立一套完整的 AI 开发过程记录、技术决策管理、问题追踪和 Git 版本管理制度。

必须保证：

- 每次交给 AI 的完整 Prompt 都可以追溯。
- 每次 AI 执行结果都有对应记录。
- 能够查询某项代码修改是由哪个任务、哪条 Prompt 引起的。
- 能够记录技术方案为什么被采用。
- 能够记录 Bug、排查过程、解决方案和经验。
- 能够通过 Git Commit 和 Tag 找到对应代码版本。
- 项目发生问题时，能够定位并恢复到之前的稳定版本。
- 不同 AI 工具可以遵循同一套开发规范。

## 三、先检查现有项目，不要直接修改

正式操作之前：

1. 检查完整项目目录结构。
2. 检查现有 `docs/` 文件夹及其中的全部文档。
3. 检查是否已经存在 `AGENTS.md`、README 和开发日志。
4. 检查 Git 当前分支、工作区状态、最近 Commit 和 Tag。
5. 了解项目当前实际技术架构。
6. 判断哪些文档已经存在，哪些需要补充。

特别注意：

- 不要覆盖已有的有效文档。
- 不要删除历史开发记录。
- 不要擅自修改项目源代码。
- 不要修改知识库 PDF、CSV、ChromaDB 数据或评测数据。
- 不要重新构建索引。
- 不要修改 API Key、环境变量和依赖配置。
- 如果发现已有文档与实际代码不一致，应记录差异，不要自行猜测。

## 四、建立统一的文档目录

在现有 `docs/` 结构基础上，建立以下管理体系。

建议结构如下：

```text
docs/
│
├── ai_workflow/
│   │
│   ├── prompts/
│   │   ├── architecture/
│   │   ├── implementation/
│   │   ├── debugging/
│   │   ├── evaluation/
│   │   └── optimization/
│   │
│   ├── execution_logs/
│   │
│   ├── decisions/
│   │
│   ├── issues/
│   │
│   ├── milestones/
│   │
│   ├── templates/
│   │
│   ├── TASK_INDEX.md
│   │
│   └── DEVELOPMENT_LOG.md
│
└── 原有项目文档保持不变
```

各目录的用途：

### 1. prompts/

保存每次交给 AI 的完整原始 Prompt。

按任务类型分类：

- architecture：架构设计。
- implementation：功能开发。
- debugging：Bug 排查。
- evaluation：检索评测。
- optimization：性能及效果优化。

文件命名：

`RAG-YYYYMMDD-001_任务名称.md`

每个任务必须有唯一 Task ID。

必须尽可能保存完整 Prompt，而不是仅保存摘要。

如果无法获取原始对话全文，只能保存实际提供给当前 AI 工具的任务指令，并明确标记记录范围，不得伪称完整记录。

### 2. execution_logs/

记录 AI 的实际执行结果。

每个执行记录必须关联对应的 Task ID 和 Prompt 文件。

至少包含：

- 执行日期。
- 使用的 AI 工具及模型（未知时明确标记）。
- 任务目标。
- 实际修改的文件。
- 每个文件的修改内容。
- 执行过的命令。
- 测试结果。
- 遇到的问题。
- 是否完成验收。
- 未解决的问题。
- 对应 Git Commit Hash（如有）。
- 下一步建议。

不得伪造测试结果、Commit Hash 或执行情况。

### 3. decisions/

记录重要技术决策。

例如：

- 为什么采用 BM25 + Vector Search。
- 为什么采用 RRF。
- 为什么使用 Cross-Encoder。
- 为什么不直接使用 Chroma Distance 作为最终排序。
- 为什么使用 SHA-256 增量索引。
- 为什么选择某种 Chunking 策略。

每份决策记录必须包含：

- 决策背景。
- 面临的问题。
- 候选方案。
- 各方案优缺点。
- 最终选择。
- 选择原因。
- 潜在风险。
- 决策日期。
- 后续是否需要重新评估。

不要将未经验证的假设记录成已经确定的事实。

### 4. issues/

记录开发中遇到的问题。

每个问题包含：

- Issue ID。
- 问题描述。
- 出现条件。
- 错误信息或日志。
- 根本原因（确认后填写）。
- 排查过程。
- 解决方案。
- 影响范围。
- 测试验证。
- 是否彻底解决。

### 5. milestones/

记录重要开发阶段。

例如：

- 初始 RAG Pipeline 完成。
- Hybrid Retrieval 完成。
- Cross-Encoder Reranking 完成。
- 检索评测体系建立。
- 增量索引完成。
- 企业级稳定性测试完成。

每个 Milestone 应关联相关 Task ID、Git Commit 和 Git Tag。

### 6. templates/

创建统一模板：

- TASK_PROMPT_TEMPLATE.md
- EXECUTION_LOG_TEMPLATE.md
- DECISION_RECORD_TEMPLATE.md
- ISSUE_TEMPLATE.md
- MILESTONE_TEMPLATE.md

确保以后新增记录时可以直接复制模板。

## 五、建立统一任务追踪机制

每次开发任务都必须生成唯一 Task ID。

例如：

`RAG-20261107-001`

同一任务的文件必须使用同一个 ID：

```text
prompts/implementation/
    RAG-20261107-001_add_feature.md

execution_logs/
    RAG-20261107-001.md

issues/
    RAG-20261107-001-ISSUE-01.md
```

TASK_INDEX.md 必须记录：

| Task ID | 任务名称 | 类型 | 执行模型 | 状态 | Commit |
|---|---|---|---|---|---|

状态建议使用：

- PLANNED
- IN_PROGRESS
- REVIEW
- COMPLETED
- BLOCKED

同一个任务不能因为更换 AI 工具而创建互相无法关联的记录。

## 六、建立强制 AI 开发工作流

以后无论使用 ChatGPT、Codex 还是 DeepSeek，都必须遵循以下流程。

### 阶段 A：任务规划

由 ChatGPT 或项目负责人负责：

1. 明确开发目标。
2. 分析现有代码。
3. 确定修改范围。
4. 确定技术方案。
5. 编写任务 Prompt。
6. 明确验收标准。
7. 生成唯一 Task ID。

### 阶段 B：Prompt 归档

在开始执行前：

1. 将完整 Prompt 保存到 prompts/ 对应目录。
2. 在 TASK_INDEX.md 登记任务。
3. 创建对应的执行记录。

### 阶段 C：AI 执行

由 Codex 或 DeepSeek 负责：

1. 阅读项目相关文档。
2. 检查实际代码。
3. 按任务要求实施修改。
4. 运行相关测试。
5. 汇报实际修改内容。
6. 不得擅自改变已确认的核心架构。

### 阶段 D：执行结果归档

任务执行完成后：

1. 更新 execution_logs。
2. 记录修改文件及实际测试结果。
3. 记录新增或解决的问题。
4. 必要时更新 decisions。
5. 更新 DEVELOPMENT_LOG.md。
6. 更新 TASK_INDEX.md。

即使任务失败，也必须记录失败原因和已完成的工作。

### 阶段 E：Git 版本管理

建立以下规范：

- 一个独立开发任务原则上对应一个独立 Commit。
- Commit Message 必须包含 Task ID。
- Commit 前必须检查 Git Diff。
- 不允许覆盖或丢弃用户尚未提交的修改。
- 不允许擅自执行 reset --hard、clean -fd 等破坏性操作。
- 不允许未经批准删除历史 Commit。
- 重要里程碑在验收通过后创建 Git Tag。
- Tag 必须关联实际存在的 Commit。

Commit Message 示例：

`feat(RAG-20261107-001): add retrieval evaluation report`

Tag 示例：

`v0.2.0-retrieval-evaluation`

本次初始化任务不要擅自提交 Commit 或创建 Tag，先完成文档体系并向我报告，等待确认。

## 七、建立项目级 AGENTS.md 规范

检查项目根目录是否已经存在 AGENTS.md。

如果不存在，创建。

如果已经存在，在原有内容基础上补充，不得直接覆盖。

必须加入以下要求：

1. 开发前阅读相关架构文档和当前任务。
2. 每项任务必须具有 Task ID。
3. 执行前保存 Prompt。
4. 执行后保存执行日志。
5. 重要技术决策必须记录。
6. Bug 必须建立问题记录。
7. 代码修改必须经过测试。
8. 重要任务需要 Git Commit。
9. 重要里程碑需要 Git Tag。
10. 不允许伪造测试结果或开发记录。
11. 不允许擅自修改生产知识库和重建索引。
12. 不允许擅自改变核心 RAG 架构。

同时说明：不同 AI 工具可能无法自动读取其他工具的聊天历史，因此必须以仓库内实际保存的 Prompt、执行记录和代码为准。

## 八、文档质量要求

这套制度需要长期使用，因此：

- 不要为了形式主义创建大量重复文档。
- 不要把所有内容堆积在一个超长 Markdown 文件里。
- 文件命名统一。
- Task ID 全局唯一。
- 文档之间必须能够相互关联。
- 使用相对路径引用项目内部文件。
- 历史记录原则上只追加，不随意覆盖。
- 已完成任务不要反复修改历史执行记录；更正时应注明更正原因。
- 不要将 API Key、密码、个人隐私或 `.env` 内容归档。
- 不要将大型 PDF、模型权重或数据库副本放入日志目录。

## 九、本次任务验收标准

完成后必须向我提供：

1. 实际创建的完整目录树。
2. 每份新建文档的用途。
3. AGENTS.md 新增或修改的规则。
4. Task ID 的生成及关联机制。
5. Prompt、执行日志和 Git Commit 如何关联。
6. 如何利用 Git 恢复历史代码版本。
7. 未来 ChatGPT 和 DeepSeek 分别应该如何使用这套制度。
8. 本次修改的完整 Git Diff 摘要。
9. 发现的原有文档与实际代码不一致的问题。

最后，请给出一份简洁的《AI 辅助开发制度使用指南》，告诉我以后每次开发一个新功能，应该如何操作。

## 十、执行原则

这次任务以建立制度和文档为唯一目标。

先检查，再规划，再实施。

只允许新增或修改本次管理制度涉及的文档，不允许修改 RAG 业务代码、知识库数据、索引和依赖。

如果遇到现有目录结构与上述建议冲突，应优先保留原有有效结构，并给出合理调整方案。

完成后停止，不要自行开始下一个 RAG 功能开发任务。

我会检查本次结果，确认制度可用后再开始下一阶段开发。

<!-- 后续用户指令：以下为本任务仍处于 REVIEW 状态时的原文追加，不改写上方原始 Prompt。 -->

## 2026-11-07 补充指令（用户原文）

/Users/luogewen/Documents/GitHub/enterprise-knowledge-agent/docs/enterprise_rag_architecture_development_guide.md你看到这个md文件了么 这个我搞的总开发架构 整个开发要用这个文档作为总指挥
