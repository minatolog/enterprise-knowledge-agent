# 制度初始化前的仓库基线审计

审计日期：2026-11-07（澳大利亚悉尼）。Task ID：`RAG-20261107-001`。本文件只记录本次只读检查，不作为新的 RAG 实现声明。

## 仓库与现有记录

- `main` 位于 `49a40dfdf00d60075cf5bfdbfd1a9f5071982cf8`；本地 `origin/main` 指向同一 Commit。未联网核对远端实时状态；`git tag --list` 为空。
- 开始前未找到项目级 `AGENTS.md`。已有根目录 `README.md`（只有简短项目简介）、`docs/devlog/`、`reports/`，以及**用户未跟踪**的 `docs/enterprise_rag_architecture_development_guide.md`。本任务不覆盖这些文件。
- 开始前另有三个未跟踪的 `.DS_Store`：根目录、`data/` 和 `data/cnooc/`。它们不是本任务的产物，本任务不删除也不暂存。
- 已有目录：`data/cnooc/`（官方 PDF 与 `sources.csv`）、`eval/`（当前 Smoke Test 与 `legacy/`）、`tests/`、`reports/`、`chroma_db/` 和 `.index_state/`。后两者、`.env` 与 PDF 被 `.gitignore` 忽略。
- `docs/devlog/001-retrieval-failure.md` 和 `002-dataset-scale-and-evaluation.md` 是历史阶段记录；`docs/devlog/readme.md` 是已有个人文本；`DevLog #003 — Real-world PDF Ingestion and Parsing Quality` 是 0 字节文件。均原样保留。

## 当前代码与数据的可核实事实

- `knowledge_config.py` 明确列出 7 份合规/治理 PDF，正式 Collection 名为 `cnooc_knowledge`。只读 `pypdf` 检查得 7 份共 106 页；本地另有年报和 ESG 报告，但不在白名单中。
- 只读 SQLite 查询 `chroma_db/chroma.sqlite3`：仅发现 `cnooc_knowledge` Collection；`embeddings` 表有 194 行。这是本机当前快照，不等于任何新环境都已建索引。
- 当前代码链路：`ingestion.py` 逐页解析 → `rag.py` 分块与来源/页码 → `document_tracker.py` SHA-256 变更检测 → `index_documents.py` 校验来源哈希并增量写 Chroma → `retrieval.py` 向量检索 + `hybrid_retrieval.py` BM25/RRF/重排 → `main.py` 构造上下文并调用 `llm.py` 的 DeepSeek → `schemas.py` 输出结构。`smoke_test_cnooc.py` 与 `evaluate_retrieval.py` 提供检索检查。本次没有调用模型 API、执行索引或修改业务代码。

## 文档与当前实现的差异

1. 用户尚未提交的 `docs/enterprise_rag_architecture_development_guide.md` 是**目标方案**：含 FastAPI、权限、日志、Docker、更多元数据和更大评测集；当前仓库的入口仍是 `main.py` 命令行程序，未见 FastAPI 服务代码。文档中 `document_id`、`document_version`、独立引用校验等也不是当前全部已实现字段/能力。不能把目标图当作现状。若日后要在 GitHub 上保留该指导，应由用户单独决定是否提交原文件。
2. [DevLog #001](../devlog/001-retrieval-failure.md) 的早期正文写“Hybrid/Reranker 未完成”，其末尾有后续实验更新；当前 `hybrid_retrieval.py` 与 `main.py` 已接入两者。阅读时按时间区分，不覆写旧日志。
3. [DevLog #002](../devlog/002-dataset-scale-and-evaluation.md) 计划扩充模拟制度并使用旧 6 题结果；当前正式语料已迁移到 CNOOC，旧评测在 `eval/legacy/`。旧指标不能作为当前真实语料的准确率。
4. [解析审计](../../reports/cnooc_ingestion_audit.md) 写于迁移前，称页码未传入 Chunk；当前 `rag.py` 已实现 PDF 页码 Chunk。该报告仍准确记录当时的解析风险，不代表当前索引接线状态。
5. [迁移报告](../../reports/cnooc_migration_report.md) 的“没有自动 Commit 或 Push”描述的是报告生成当时；此后已有 `49a40df` Commit。报告中的其他数据是历史验收证据，当前 Collection 行数和 PDF 页数已在上文重新核对。

历史 ChatGPT、Codex、DeepSeek 对话的完整 Prompt 目前不在仓库，不能从 Commit 或日志逆向重建。新制度从本 Task ID 开始记录实际收到的指令；旧任务若补录，须写明可取得的原始材料范围。

## 后续确认（2026-11-07）

用户明确指定 `docs/enterprise_rag_architecture_development_guide.md` 为**整个项目的总开发架构指导**。本节是后续确认，不改变上方“文件在基线时尚未跟踪”和“目标架构不等于当前实现”的事实。该指导第 14 节提及的 `docs/development/`、`docs/decisions/` 是当时的建议路径；本次用户指定的 AI 管理目录采用 `docs/ai_workflow/execution_logs/` 与 `docs/ai_workflow/decisions/` 承接同样的留痕职责，原指导文档不作改写。
