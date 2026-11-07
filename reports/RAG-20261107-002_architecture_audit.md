# RAG-20261107-002 当前 RAG 架构审计报告

- 审计日期：2026-11-07（Australia/Sydney）
- 最后修订：2026-11-08（Australia/Sydney）
- Task ID：`RAG-20261107-002`
- 审计性质：只读架构审计；本次不开发新功能
- 审计工具/模型：VS Code GitHub Copilot（DeepSeek V4.1 Flash）
- 代码基线（审计当时，2026-11-07）：`main` @ `49a40dfdf00d60075cf5bfdbfd1a9f5071982cf8`；本地 `origin/main` 同值；本地无 Git Tag
- 工作区状态（审计当时）：存在用户原有未跟踪文件；已跟踪文件无改动，暂存区为空
- 后续状态（2026-11-08 修订时）：HEAD 已前进到 `2bbaa9c`（`创建prompt 管理`），治理文档与审计报告已提交；本轮修订产生未提交改动，详见 2.5 与 11.6。
- 时间口径：除特别注明外，正文中的“当前”指 2026-11-07 审计当时；2026-11-08 修订只修正报告结论与记录，未重新运行审计、模型或索引。
- 报告状态：`REVIEW`，等待用户确认下一阶段优先级；本次未实施任何后续任务

## 0. 结论摘要

1. **离线入库主链路真实存在，且当前快照与代码基本对齐。** 白名单 7 份 CNOOC PDF、`sources.csv` 合计 106 页；当前代码重新切块得到 194 个唯一 Chunk；Chroma 中 `cnooc_knowledge` 有 194 条记录，Chunk ID 集合与当前切块结果完全一致；Chroma Metadata 与 BM25 都从同一批记录出发。
2. **在线问答仍是命令行原型，不是 API 服务。** 入口是 `main.py` 的交互式 CLI；仓库没有 FastAPI 路由、请求 ID、生产日志、鉴权/ACL、Docker 或 `.env.example`。`requirements.txt` 中出现 `uvicorn`、`pydantic-settings`、OpenTelemetry 包，但没有 `fastapi`，不能据此认定 API 已完成。
3. **P0 的最大缺口是“可信评测”而不是“再写一个接口”。** 当前 CNOOC 评测只有 7 题，且全部是有答案题，没有无答案/拒答题；`evaluate_retrieval.py` 只算 Hit@1、Hit@3、MRR@3，不保存运行配置，也不做引用/答案正确性检查。旧模拟制度的 6 题结果（Reranker Hit@1 100%）不能用于当前语料。
4. **历史 Smoke Test 线索已复核。** 解析既有 `reports/cnooc_migration_smoke.json` 后，严格按“来源 + 页码 + 证据片段”匹配：Vector Top-1 2/7、Top-3 6/7；Hybrid Top-1 4/7、Top-3 6/7；Hybrid + Reranker Top-1 4/7、Top-3 5/7。这是 7 题接线检查，**不是正式准确率**，本次也没有重新运行模型。
5. **高风险点集中在正确性与可复现性：** 页码错位/错文档、Reranker 高分但页码不对、无证据问题只靠 Prompt 拒答、引用有来源标签映射但缺 Chunk 级字段与语义支持校验、LLM/CLI 异常处理薄弱、PDF/Chroma/状态文件被 Git 忽略导致新环境无法复现、README 只有两行。
6. **建议的最小顺序：** 先把评测基线做可信（约 30 题，含无答案；任务 1 记录当前系统基线）→ 再集中配置并补 request ID/阶段日志/结构化错误 → 再做证据充分性判断与引用校验（任务 3，比较改进前后）→ 再包 FastAPI 最小闭环 → 最后补 README、`.env.example` 和可复现 Demo。Docker、ACL、Query Rewrite、GraphRAG、OCR、年报/ESG 入库暂缓。

## 1. 审计边界、方法与证据标签

### 1.1 实际审计范围

本次实际阅读/核对：

- 总指导：`docs/enterprise_rag_architecture_development_guide.md` 的第 1、3、4、5、6、8、10、11、14、15 节（实际通读了全文）。
- 制度：根 `AGENTS.md`、`docs/ai_workflow/README.md`、`TASK_INDEX.md`、`DEVELOPMENT_LOG.md`、`BASELINE_AUDIT.md`、`RAG-20261107-001` 与 `RAG-20261107-002` 的执行记录、现有 Prompt 归档。
- 代码：`knowledge_config.py`、`ingestion.py`、`rag.py`、`document_tracker.py`、`index_documents.py`、`retrieval.py`、`hybrid_retrieval.py`、`main.py`、`llm.py`、`schemas.py`、`evaluate_retrieval.py`、`smoke_test_cnooc.py`、`calibrate_threshold.py`、`structured_output.py`。
- 测试与评测：`tests/test_ingestion.py`、`tests/test_cnooc_migration.py`、`eval/cnooc_smoke_cases.json`、`eval/legacy/*.json`。
- 报告与日志：`reports/cnooc_ingestion_audit.md/.json`、`reports/cnooc_migration_report.md`、`reports/cnooc_migration_smoke.json`、`docs/devlog/001-retrieval-failure.md`、`docs/devlog/002-dataset-scale-and-evaluation.md`、`docs/devlog/readme.md`、`docs/devlog/DevLog #003 — Real-world PDF Ingestion and Parsing Quality`。
- Git：分支、HEAD、最近提交、Tag、`git status`、已跟踪文件与忽略规则。
- 本地只读数据：`chroma_db/chroma.sqlite3`（SQLite `mode=ro&immutable=1`）、`.index_state/cnooc_document_hashes.json`、`data/cnooc/sources.csv`。
- Prompt 追溯：Codex 编写的原始任务 Prompt 已完整归档在 `docs/ai_workflow/prompts/architecture/RAG-20261107-002_current_architecture_audit.md`；用户确认截图显示这份任务指令。DeepSeek 记录的聊天版与归档版有措辞差异，差异表见 `docs/ai_workflow/issues/RAG-20261107-002-ISSUE-01.md`；聊天版全文尚未单独归档，不能据差异表声称逐字留痕已完成。

未执行：索引重建、Embedding 计算、检索/重排模型推理、DeepSeek API 调用、Git Commit/Tag/Push、对业务代码/PDF/Chroma/状态文件/评测数据的写入。

### 1.2 证据标签定义

| 标签 | 含义 |
|---|---|
| **已实现且本次验证** | 代码存在，且本次通过只读检查或测试观察到了对应行为 |
| **代码存在但未验证** | 代码存在，但运行它会写数据、加载模型或调用外部 API，本次未执行；可能只有历史记录 |
| **仅历史报告记录** | 只有历史报告/日志/JSON 声称该结果，本次未复现 |
| **未实现** | 没有对应代码、入口、依赖或配置 |

### 1.3 历史线索的处理

用户给出的历史线索（7 份 PDF、106 页、194 Chunk、`cnooc_knowledge`、Reranker Top-1 4/7、Top-3 5/7、最近 Commit `49a40df`）均已重新核对。其中 PDF/Chunk/Collection/Commit 与当前本地快照一致；Smoke Test 结果通过解析既有 JSON 复核，但没有重新运行模型，因此仍只能标为“历史报告记录”。

## 2. 真实目录结构与入口

### 2.1 当前目录树（只列审计相关项）

目录树中的“未跟踪”注释是审计当时（2026-11-07）的状态；2026-11-08 修订时 `AGENTS.md`、`docs/ai_workflow/`、总指导和本报告已随 `2bbaa9c` 提交。

```text
enterprise-knowledge-agent/
├── AGENTS.md                         # 未跟踪；AI 协作规则
├── README.md                         # 仅 2 行项目简介
├── calibrate_threshold.py            # 旧 Reranker 阈值校准脚本
├── document_tracker.py               # SHA-256 变更检测与状态文件
├── evaluate_retrieval.py             # 三路检索对照评测
├── hybrid_retrieval.py               # BM25、RRF、Cross-Encoder Reranker
├── index_documents.py                # 增量写入 Chroma
├── ingestion.py                      # PDF/MD/TXT/DOCX 读取
├── knowledge_config.py               # 路径、模型、Collection、白名单
├── llm.py                            # DeepSeek 调用与 Prompt
├── main.py                           # 命令行问答入口
├── rag.py                            # Chunking 与元数据
├── requirements.txt                  # 依赖清单
├── retrieval.py                      # Chroma 向量检索
├── schemas.py                        # Pydantic 输出模型
├── smoke_test_cnooc.py               # 7 题 Smoke Test，写 reports/
├── structured_output.py              # 独立 DeepSeek 结构化输出示例
├── tests/
│   ├── test_cnooc_migration.py
│   └── test_ingestion.py
├── eval/
│   ├── cnooc_smoke_cases.json        # 当前 CNOOC 7 题
│   └── legacy/
│       ├── retrieval_cases.json      # 旧模拟制度 7 题
│       ├── threshold_cases.json      # 旧模拟制度 12 题
│       └── threshold_results.json
├── reports/
│   ├── cnooc_ingestion_audit.json
│   ├── cnooc_ingestion_audit.md
│   ├── cnooc_migration_report.md
│   └── cnooc_migration_smoke.json
├── data/cnooc/
│   ├── compliance/
│   │   ├── employee_compliance.pdf
│   │   └── director_ethics_2026.pdf
│   ├── governance/
│   │   ├── articles_2025.pdf
│   │   ├── nomination_committee_2025.pdf
│   │   ├── audit_committee.pdf
│   │   ├── remuneration_committee.pdf
│   │   └── strategy_sustainability_committee.pdf
│   ├── finance/annual_report_2025.pdf          # 存在但不在白名单
│   ├── sustainability/esg_report_2025.pdf     # 存在但不在白名单
│   └── sources.csv                             # 9 行；Git 跟踪
├── chroma_db/                         # Git 忽略；本地向量库
├── .index_state/                      # Git 忽略；增量状态
├── .env                              # Git 忽略；本次未读取
└── docs/
    ├── enterprise_rag_architecture_development_guide.md   # 未跟踪
    ├── ai_workflow/                   # 未跟踪；制度、Prompt、执行记录
    └── devlog/                        # 历史开发日志
```

### 2.2 当前入口

| 入口 | 用途 | 是否实际存在 |
|---|---|---|
| `python main.py` | 交互式提问 → Hybrid + Reranker → DeepSeek → JSON | 存在 |
| `python index_documents.py` | 校验白名单/SHA-256 → 增量写入 Chroma | 存在 |
| `python rag.py` | 打印当前白名单 Chunk | 存在 |
| `python evaluate_retrieval.py --dataset <json>` | Vector / Hybrid / Reranker 对照 | 存在 |
| `python smoke_test_cnooc.py` | 7 题 Smoke Test，写 `reports/cnooc_migration_smoke.json` | 存在 |
| `python calibrate_threshold.py --dataset <json> --output <json>` | 旧阈值校准 | 存在，但依赖 `answerable` 字段 |
| `python structured_output.py` | 独立结构化输出示例；导入即调用 API | 存在，但不属于主流程 |
| `python -m unittest discover -s tests -v` | 测试 | 存在；其中 1 个测试会打开 Chroma |

### 2.3 逐文件核对清单

| 路径 | 状态 | 说明 |
|---|---|---|
| `knowledge_config.py` | **存在** | 白名单、Collection、Embedding/Reranker 模型、路径 |
| `ingestion.py` | **存在** | PDF/MD/TXT/DOCX 读取 |
| `rag.py` | **存在** | Chunking 与元数据 |
| `document_tracker.py` | **存在** | SHA-256 变更检测 |
| `index_documents.py` | **存在** | 增量写入 Chroma |
| `retrieval.py` | **存在** | Chroma 向量检索 |
| `hybrid_retrieval.py` | **存在** | BM25、RRF、Reranker |
| `main.py` | **存在** | CLI 问答入口 |
| `llm.py` | **存在** | DeepSeek 调用 |
| `schemas.py` | **存在** | `RAGResponse` |
| `evaluate_retrieval.py` | **存在** | 三路检索对照 |
| `smoke_test_cnooc.py` | **存在** | 7 题 Smoke Test |
| `tests/` | **存在** | `test_ingestion.py`、`test_cnooc_migration.py` |
| `eval/` | **存在** | `cnooc_smoke_cases.json`、`legacy/` 三份 JSON |
| `reports/` | **存在** | 迁移报告、解析审计、Smoke JSON |
| `docs/` | **存在** | 总指导、`ai_workflow/`、`devlog/` |

### 2.4 不存在或缺失的项

以下路径/能力本次检查为**不存在**：

- `app/`（FastAPI 路由、core、services 等）
- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `docs/architecture/`
- `docs/development/`
- `docs/testing/`
- `scripts/`
- `tests/__init__.py`（不是运行测试的硬性要求，但说明 tests 不是包）
- FastAPI 路由/服务代码（`grep` 未发现生产代码中的 `FastAPI`、`APIRouter`、`request_id`）
- 生产日志代码（`grep` 仅发现测试中设置 `pypdf` 日志级别）
- 权限/ACL/租户字段
- Docker 部署配置

### 2.5 Git 状态

以下命令与结果是**审计当时（2026-11-07）**的状态；2026-11-08 修订时仓库已前进，不能把下面的 HEAD/未跟踪列表当作修订时状态。

```text
$ git branch --show-current
main
$ git log -1 --format='%H%n%ad%n%s'
49a40dfdf00d60075cf5bfdbfd1a9f5071982cf8
Thu Oct 29 19:21:24 2026 +1100
feat: 将知识库迁移为中海油专属知识库
$ git tag --sort=-creatordate
（无输出）
$ git status --porcelain=v1
?? .DS_Store
?? AGENTS.md
?? data/.DS_Store
?? data/cnooc/.DS_Store
?? docs/ai_workflow/
?? docs/enterprise_rag_architecture_development_guide.md
$ git diff --stat
（无输出）
$ git diff --cached --stat
（无输出）
```

- 审计当时分支 `main`；HEAD 为 `49a40df`；本地 `origin/main` 指向同一 Commit；本地没有 Tag。
- 审计当时 `AGENTS.md`、`docs/ai_workflow/`、总指导文件均**未被 Git 跟踪**；本次没有暂存或提交它们。2026-11-08 修订时，这些文件以及本报告已随 `2bbaa9c`（`创建prompt 管理`）提交。
- PDF 被 `.gitignore:186-187` 的 `data/cnooc/**/*.pdf` 忽略；`chroma_db/` 与 `.index_state/` 被 `.gitignore:182-183` 忽略；`.env` 被 `.gitignore:131` 忽略。
- 2026-11-08 修订时实际状态：HEAD `2bbaa9c`；`docs/ai_workflow/DEVELOPMENT_LOG.md`、`TASK_INDEX.md`、`execution_logs/RAG-20261107-002.md` 及本报告有未提交修改；`docs/ai_workflow/issues/RAG-20261107-002-ISSUE-01.md` 与 `docs/ai_workflow/prompts/architecture/RAG-20261107-002_audit_report_revision.md` 未跟踪；暂存区为空。
- 未联网 `git fetch`，因此远端实时状态未知；以上只代表本地引用。

## 3. 离线入库流水线

### 3.1 步骤、输入、输出与文件映射

| 步骤 | 输入 | 输出 | 负责文件 | 本次证据/说明 |
|---|---|---|---|---|
| 1. 白名单与路径校验 | `INDEXED_DOCUMENTS` 中的 7 条相对路径 | 7 个 `Path` | `knowledge_config.py:15-33` | 只允许 `data/cnooc/` 下、扩展名为 `.pdf` 的文件；缺失文件默认报错 |
| 2. 来源清单与原件哈希 | `data/cnooc/sources.csv` + 白名单文件 | 每份文件的 CSV 行 | `index_documents.py:18-25` | 逐份比较 SHA-256；不一致直接抛错 |
| 3. PDF 逐页解析 | PDF 路径 | `pages`（页码 + 文本 + 页错误）、`text`、`page_count` | `ingestion.py:20-100` | 单页失败记录到 `page_errors` 并警告；整份无可提取文本才报错 |
| 4. Chunking | `document` 字典 | Chunk 列表 | `rag.py:112-174` | PDF 按页、页内按行累积到约 700 字符；长行退回 700/80 字符切分 |
| 5. 增量检测 | 当前白名单文件 SHA-256 + `.index_state/cnooc_document_hashes.json` | `added` / `modified` / `deleted` / `unchanged` | `document_tracker.py:9-104` | 状态文件当前 7 条；删除/移出白名单会进入 `deleted` |
| 6. Embedding | Chunk 文本列表 | 归一化向量 | `index_documents.py:27-37` | `BAAI/bge-small-zh-v1.5`；`normalize_embeddings=True`；`batch_size=32` |
| 7. 写 Chroma | Chunk ID、文本、向量、Metadata | `cnooc_knowledge` 中的记录 | `index_documents.py:27-64` | 每 64 条 `upsert`；写入前先算完全部向量；写完删除该文档的旧 Chunk |
| 8. 清理、校验、保存状态 | Collection + 当前路径 | 每份文档 Chunk 数 | `index_documents.py:66-118` | 清理已删除文档和孤儿 Chunk；校验路径/知识库/页码；仅在成功后 `save_state` |

### 3.2 来源、页码和 Chunk ID 保存在哪里

- **Chunk ID**：写入 Chroma 的字符串主键，格式为
  `data/cnooc/...pdf::p0006::c0001`（PDF）或 `...::c0001`（非 PDF）；
  见 `rag.py:147` 与 `rag.py:179`。
- **来源路径**：Chunk 字段 `relative_path`，同时写入 Chroma Metadata；
  `source` 是文件名；两者都由 `rag.py` 生成。
- **页码**：`page_start` / `page_end`，当前 PDF 每个 Chunk 都只属于一页，所以两者相等；
  写入 Chroma Metadata，见 `rag.py:152-153` 与 `index_documents.py:39-45`。
- **官方链接**：`source_url` 来自 `sources.csv`，写入 Chroma Metadata，但**没有进入最终回答的 sources**。
- **文档标题/分类/版本**：`sources.csv` 中有 `document_title`、`category`、`publication_date`、`version`，
  但 `index_documents.py:39-45` 没有把它们写入 Chunk Metadata。
- **增量状态**：`.index_state/cnooc_document_hashes.json`，只保存“相对路径 → SHA-256”，
  不保存索引版本、Embedding 版本或文档版本。

### 3.3 本次只读核对结果

实际只读检查（不写库、不计算 Embedding）：

```text
当前代码 build_chunks(): 194 chunks；唯一 ID 194 个
每份文档 Chunk 数：
  employee_compliance.pdf                    43
  director_ethics_2026.pdf                   29
  articles_2025.pdf                          89
  nomination_committee_2025.pdf               4
  audit_committee.pdf                        18
  remuneration_committee.pdf                  7
  strategy_sustainability_committee.pdf       4
页码范围非法（page_start < 1 或 page_end != page_start）：0
Chroma `cnooc_knowledge`：194 条 embedding；Chunk ID 集合与 build_chunks() 完全相等
Chroma Metadata：194 条记录 × 8 个 key（relative_path、knowledge_base、section、
  page_start、page_end、source、source_url、chroma:document）
`.index_state/cnooc_document_hashes.json`：7 条
`sources.csv`：9 行（7 份白名单 + 年报 + ESG）
```

白名单 7 份页数合计：27 + 16 + 43 + 3 + 10 + 4 + 3 = **106 页**。`tests/test_ingestion.py:60-82` 还核对了 9 份 PDF 的实际页数与 `sources.csv` 一致、页码从 1 连续、无 `page_errors`；本次该测试通过。

### 3.4 入库侧未实现或未验证的点

- **OCR / 版面感知解析**：未实现；仍使用 `pypdf` 纯文本提取。
- **表格语义**：未实现；页内按行/字符切分，无法保证表头与数字列对应。
- **解析失败的索引留痕**：`page_errors` 只存在于解析结果和警告中，Chroma Metadata 不记录哪些页失败。
- **文档标题/分类/版本 Metadata**：未实现；`sources.csv` 有数据但未传入索引。
- **独立 `document_id`**：未实现；`relative_path` 同时充当文档身份，文件重命名会被视为删除 + 新增。
- **持久化 BM25 索引**：未实现；BM25 在查询进程内从 Chroma 重建。
- **索引版本/Embedding 版本**：未实现；状态文件只有文件哈希，Chroma 不记录 Embedding 模型名/版本。
- **写入事务**：`upsert` 按 64 条分批，跨批次不是原子操作；中途失败可能留下部分新 Chunk，但下次运行可重试修复。本次没有做故障注入验证。

## 4. 在线问答流水线

### 4.1 步骤、输入、输出与文件映射

当前真实入口是 `main.py` 的交互式 CLI，不是 HTTP API。

| 步骤 | 输入 | 输出 | 负责文件 | 说明 |
|---|---|---|---|---|
| 1. 读取问题 | 终端输入 | 去首尾空白的字符串 | `main.py:19-26` | 仅检查空字符串；无长度/编码/规范化处理 |
| 2. Hybrid 召回 | 问题 | 向量 Top-10 + BM25 Top-10 | `hybrid_retrieval.py:49-61` | `candidate_k = max(10, k)` |
| 3. RRF 融合 | 两路排名 | 按 Chunk ID 去重后的 Top-5 | `hybrid_retrieval.py:49-61` | `1 / (60 + rank)`；保留 `rrf_score` |
| 4. Reranker | 问题 + 5 个候选文本 | 重排后的 Top-3 | `hybrid_retrieval.py:64-73` | `BAAI/bge-reranker-base`；保留 `rerank_score` |
| 5. Context Builder | Top-3 Chunk | `[资料 N]` 文本块 | `main.py:54-70` | 只有来源路径 + 页码 + 正文；无 Token 预算/去重 |
| 6. LLM 生成 | 问题 + Context | 回答文本 | `llm.py:13-49` | `deepseek-flash`；Prompt 要求引用 `[资料 N]` |
| 7. 引用映射 | 回答中的 `[资料 N]` + 本次检索结果 | `sources` 字符串列表 | `main.py:82-87` | 编号 → 来源标签；越界编号忽略；不做 Chunk 级或语义支持校验 |
| 8. 结构化输出 | 回答 + sources + rerank_score | `RAGResponse` JSON | `main.py:88-96`、`schemas.py:5-8` | `sources: list[str]`，无 request_id、无 chunk_id |
| 9. 异常处理 | 任意异常 | 终端打印 | `main.py:93-96` | `print` 后正常退出，退出码为 0 |

### 4.2 五个组件的职责边界

| 组件 | 职责 | 不负责 |
|---|---|---|
| Chroma Dense Retrieval | 用 BGE 查询向量做向量召回；返回 Chunk ID、文本、Metadata、距离 | 不做关键词匹配、不做融合、不做拒答 |
| BM25 | 用 Jieba 分词 + `BM25Okapi` 做关键词召回；语料来自 Chroma 全量记录 | 不持久化、不写回 Chroma、不做融合 |
| RRF | 用两路排名计算融合分，按 Chunk ID 去重 | 不比较原始分数绝对值、不做阈值判断 |
| Cross-Encoder Reranker | 对已召回候选重新打分排序 | 不能找回第一阶段漏掉的文档；不保证页码/证据正确 |
| LLM | 基于 Context 生成回答，并按 Prompt 要求引用资料编号 | 不访问 Chroma/BM25；不自行校验引用是否真实；不负责权限过滤 |

### 4.3 来源、页码、Chunk ID 在在线链路中的位置

- `retrieval.py:39-49` 返回 `chunk_id`、`source`、`relative_path`、`page_start`、`page_end`、`section`、`source_url`、`distance`。
- `hybrid_retrieval.py` 在 RRF 和 Reranker 中保留这些字段，并追加 `rrf_score` / `rerank_score`。
- `main.py:13-16` 的 `source_label()` 的输入是检索结果中的 `relative_path`、`page_start`、`page_end`，所以来源标签不是凭空生成，而是由真实检索元数据生成。
- `main.py:82-86` 把回答中的 `[资料 N]` 映射到 `source_by_number`（本次检索结果的来源标签）；越界编号会被忽略，但映射只到字符串标签，不到 Chunk ID。
- Context 只包含 `[资料 N]`、来源标签、正文；**没有 Chunk ID**。
- 最终 `RAGResponse.sources` 是 `list[str]`，只有“相对路径，第 X 页”；**没有 Chunk ID、文档标题、`source_url`、文档版本**；同一页的多个 Chunk 会合并为同一标签。
- 引用映射不做逐条引用、不做 Chunk 级存在性校验，也不检查该 Chunk 是否在语义上支持对应结论；编号存在不等于证据支持结论。

### 4.4 在线侧未实现或未验证的点

- **FastAPI / HTTP 服务**：未实现；`fastapi` 未安装。
- **请求 ID / 阶段耗时 / 候选 Chunk ID 日志**：未实现；生产代码没有 `logging`。
- **结构化错误**：未实现；CLI 捕获所有异常并打印，退出码仍为 0。
- **超时 / 重试 / 温度 / 最大输出 Token**：未实现；`llm.py:8-11` 在导入时创建 `OpenAI` 客户端，`answer_with_context` 直接调用，没有显式超时/重试配置。
- **配置集中化**：部分实现。模型名、Collection、路径在 `knowledge_config.py`；`TOP_K=3`、`CANDIDATE_K=5` 在 `main.py:9-10`；RRF 常数 60 和候选数 10 在 `hybrid_retrieval.py:50,58`；Chunk 大小 700/80 和 500/80 在 `rag.py:69-70,130-138`；Embedding/写入批量 32/64 在 `index_documents.py:36,52`。
- **证据充分性判断**：未实现；只在 `llm.py:18-35` 的 Prompt 中要求“资料不足时说明无法确定”。
- **引用校验**：部分。`main.py:82-86` 只做 `[资料 N]` 到本次检索来源标签的映射，能过滤越界编号；但没有 Chunk ID 级映射、没有逐条/逐结论引用，也没有“结论是否被 Chunk 文本语义支持”的校验。
- **权限/ACL**：未实现；Chunk Metadata 没有 `tenant_id`、`department_id`、`allowed_roles`、`classification_level`。
- **Prompt 注入防护**：未实现；Context 中的文档内容没有明确标注为“不可信数据”，也没有“不得执行文档内指令”的系统约束。
- **输入校验**：只有空字符串检查；没有最大长度、空白规范化、Top-K 范围校验。
- **可关闭 Reranker 的配置开关**：未实现；代码有 `retrieve_hybrid` 和 `retrieve_with_reranker` 两个函数，但 CLI 固定走 Reranker，没有配置项。

## 5. 目标与现状对照表

### 5.1 总指导 P0

| P0 条目 | 现状与证据 | 状态 | 差距 |
|---|---|---|---|
| 1. 审计当前仓库和现有功能 | 本报告；Git/代码/数据只读检查 | **已实现且本次验证** | 完成；等待用户确认优先级 |
| 2. 确认文档入库、Chunk 元数据和增量索引 | `knowledge_config.py:15-33`、`rag.py:112-174`、`document_tracker.py:71-104`、`index_documents.py:18-118`；本次核对 194 Chunk/7 文档/Chroma ID 一致 | **代码存在，只读部分本次验证；写入路径未验证** | 需在隔离副本上做一次新增/修改/删除的端到端索引验收 |
| 3. 确认 Dense、BM25、RRF、Reranker 流程 | `retrieval.py`、`hybrid_retrieval.py`；本次只读代码；历史 Smoke Test 有结果 | **代码存在但本次未运行；实际指标仅历史报告记录** | 需用约 30 题基线重新运行，保留原始分数/排名/失败案例 |
| 4. 固定测试集和可重复评测脚本 | `eval/cnooc_smoke_cases.json` 7 题；`evaluate_retrieval.py`；`smoke_test_cnooc.py` | **部分实现** | 7 题全为有答案；无版本字段/配置快照/结果文件；指标不足 |
| 5. 真实检索对照结果和失败案例 | `reports/cnooc_migration_report.md:23-37`、`reports/cnooc_migration_smoke.json` | **仅历史报告记录** | 7 题 Smoke，不是正式准确率；本次未重跑 |
| 6. FastAPI 封装核心问答 | 无 `app/`；`fastapi` 未安装（`fastapi installed: False`）；`requirements.txt` 有 `uvicorn` 但无 `fastapi` | **未实现** | 需新增 API 层与请求/响应模型 |
| 7. 统一请求/响应和异常处理 | `schemas.py:5-8` 只有 `RAGResponse`；`main.py:93-96` 捕获并打印 | **部分/未实现** | 无 API schema、无错误码、无 request_id、CLI 失败退出码为 0 |
| 8. request ID、阶段耗时、基础日志 | 生产代码无 `logging`/`request_id`；仅测试设置 `pypdf` 日志级别 | **未实现** | 需 Python logging + request ID + 阶段耗时/候选 ID |
| 9. README、架构图、环境配置、运行说明 | `README.md` 仅 2 行；无 `.env.example`；无架构图；总指导与制度文件在审计当时未跟踪，修订时已随 `2bbaa9c` 提交 | **部分实现/交付严重不足** | 新环境无法按 README 启动；需完整运行手册 |
| 10. 可运行本地 Demo | `main.py` CLI 存在；历史报告记录一次 DeepSeek 端到端成功 | **部分实现** | 只有 CLI，无 API Demo；本次未重跑 |

**P0 验收结论：未满足。** 主要卡点是评测可信度、API、日志/错误契约、README/环境复现，而不是检索算法本身。

### 5.2 总指导 P1

| P1 条目 | 现状与证据 | 状态 | 差距 |
|---|---|---|---|
| 文档新增/修改/删除一致性 | `document_tracker.py:71-104` + `index_documents.py:84-118`；`test_missing_selected_document...` 通过 | **代码存在但端到端未验证** | 需真实写入/删除测试；当前只验证了变更检测，不验证 Chroma/BM25 最终状态 |
| 文档版本和索引版本管理 | `sources.csv` 有 `version`/`publication_date`；Chunk Metadata 没有；状态文件只有哈希 | **部分/未实现** | 需把标题/分类/版本写入 Metadata，并记录索引版本/Embedding 版本 |
| 更完善的日志与错误追踪 | 无生产日志 | **未实现** | 与 P0-8 合并做 |
| Docker 本地运行 | 无 `Dockerfile`/`docker-compose.yml` | **未实现** | 暂缓到 API 稳定后 |
| 基础上传安全 | 无上传接口 | **未实现/当前不适用** | 暂缓到 `/documents/ingest` 设计时 |
| 失败案例分析 | Smoke JSON + 迁移报告有 3 个失败案例 | **仅历史记录** | 需系统化失败分类与回归用例 |
| 模型/检索器/存储层可替换性 | 代码按文件分了 ingestion/retrieval/generation，但模型名和参数硬编码，无接口抽象 | **部分** | 先集中配置；不必为抽象而大规模搬迁 |

### 5.3 总指导 P2

| P2 条目 | 现状 | 状态 | 建议 |
|---|---|---|---|
| 文档级 ACL / RBAC | 无 ACL 字段/过滤 | **未实现** | 暂缓；单官方知识库暂无业务需求 |
| Query Rewrite / 多查询检索 | 无 | **未实现** | 暂缓；先用评测证明收益 |
| 更多数据源连接器 | 只有本地 PDF/MD/TXT/DOCX 读取 | **未实现** | 暂缓 |
| Agent / LangGraph 调用 RAG | 无 | **未实现** | 暂缓 |
| Long-Context 与 RAG 对比 | 无 | **未实现** | 暂缓；可选实验 |
| GraphRAG、多模态检索 | 无 | **未实现** | 暂缓；明确不在当前范围 |

### 5.4 目标架构横向能力

| 目标能力 | 当前实现 | 状态 |
|---|---|---|
| 解析、清洗、OCR（按需） | `pypdf` 逐页解析；无 OCR；无版面感知 | **部分** |
| Chunk 稳定 ID、来源、页码 | 有稳定 ID、相对路径、页码；无 `document_id`/标题/版本 Metadata | **部分** |
| Dense Retrieval + Chroma | 已实现；`cnooc_knowledge` 194 条 | **已实现且本次验证（快照）** |
| BM25 与 Chroma 同一批 Chunk | 代码从 Chroma 重建 BM25；本次只读核对 ID 集合一致 | **代码存在但本次未运行** |
| RRF | 已实现；参数硬编码 | **代码存在但本次未运行** |
| Cross-Encoder Reranker | 已实现；参数/开关未配置化 | **代码存在但本次未运行** |
| Context Builder | 固定 3 条、无 Token 预算/去重 | **部分** |
| LLM 生成 | DeepSeek `deepseek-flash`；无超时/重试/温度配置 | **代码存在但本次未运行** |
| 证据不足时说明 | 仅 Prompt 约束 | **未实现（独立检查）** |
| 引用来自真实元数据 | 来源标签由检索结果的路径/页码生成；缺 Chunk ID/标题/URL/版本；无 Chunk 级与语义支持校验 | **部分** |
| FastAPI | 无 | **未实现** |
| 身份校验/权限过滤 | 无 | **未实现** |
| 日志/Trace | 无 | **未实现** |
| Docker/部署 | 无 | **未实现** |
| 评测/回归 | 7 题 Smoke + 旧模拟评测 | **部分** |
| README/架构图/运行说明 | README 2 行；无 `.env.example` | **未实现/严重不足** |

### 5.5 关键目标与现状差距

1. **目标架构中的 API、权限、日志、Docker、引用校验、证据充分性都没有落地**；当前是“单机 CLI + 混合检索原型”。
2. **目标要求引用至少包含文档标题、来源路径、页码和 Chunk ID**；当前来源标签确实由检索结果的路径/页码生成，但没有标题/Chunk ID/URL/版本，也没有 Chunk 级映射和语义支持校验。
3. **目标要求固定评测集逐步达到约 30 题**；当前 CNOOC 只有 7 题，且没有无答案题。
4. **目标要求配置集中化**；当前模型名/路径集中了，但 Top-K、RRF、Chunk 大小、批量大小、阈值仍散落在代码中。
5. **目标要求文档版本/索引版本管理**；当前只有文件 SHA-256，Chroma 不记录 Embedding 模型/版本。
6. **目标要求日志/请求 ID/阶段耗时**；当前生产代码完全没有日志。

## 6. 测试覆盖与评测证据

### 6.1 单元/集成测试

| 测试 | 验证内容 | 本次结果 |
|---|---|---|
| `tests/test_ingestion.py::test_default_scope_stays_shallow_and_explicit_scope_is_recursive` | 默认只扫顶层；显式递归；符号链接去重 | **通过** |
| `tests/test_ingestion.py::test_old_text_and_docx_readers` | MD/TXT/DOCX 读取 | **通过** |
| `tests/test_ingestion.py::test_bad_pdf_reports_failure_without_stopping_batch` | 空白 PDF 报错但不阻断批次 | **通过** |
| `tests/test_ingestion.py::test_real_pdf_page_metadata_and_corpus_isolation` | 9 份真实 PDF 页数/页码/路径与 CSV 一致；旧模拟文件不在语料 | **通过** |
| `tests/test_cnooc_migration.py::test_allowlist_and_original_hashes` | 7 份白名单；`sources.csv` 9 行；SHA-256 一致 | **通过** |
| `tests/test_cnooc_migration.py::test_chunks_have_stable_page_metadata` | 194 Chunk；唯一 ID；页码/知识库/路径正确 | **通过** |
| `tests/test_cnooc_migration.py::test_bm25_and_vector_use_identical_ids` | Chroma ID 与 BM25 语料 ID 相同 | **未运行**；该测试会打开 Chroma `PersistentClient`，可能写库。已用 SQLite 只读查询做等价 ID 核对 |
| `tests/test_cnooc_migration.py::test_state_is_stable_and_legacy_files_are_outside_data` | 状态稳定；旧模拟文件不在 `data/`；旧状态存在 | **通过** |
| `tests/test_cnooc_migration.py::test_missing_selected_document_is_detected_for_cleanup` | 缺失白名单文件进入 `deleted` | **通过** |

**覆盖缺口：**

- 没有检索排序测试（Vector/BM25/RRF/Reranker 的实际排序断言）。
- 没有引用提取、编号映射、拒绝伪造引用或语义支持校验的测试。
- 没有 LLM 超时/异常/无 Key 的测试。
- 没有 FastAPI 集成测试。
- 没有索引写入、更新、删除的端到端测试（只在隔离副本上做才安全）。
- 没有 PDF 表格、乱码页、跨页条款的专门测试。
- 没有评测脚本自身的测试（数据集字段、指标计算、结果持久化）。

### 6.2 当前 CNOOC 评测口径

| 数据集 | 题数 | 有答案 | 无答案 | 字段 | 用途 |
|---|---:|---:|---:|---|---|
| `eval/cnooc_smoke_cases.json` | 7 | 7 | 0 | `question`、`expected_source`、`expected_page`、`evidence` | 小型接线检查 |

- `evaluate_retrieval.py` 只计算 `Hit@1`、`Hit@3`、`MRR@3`（`evaluate_retrieval.py:62-64`）。
- `evaluate_retrieval.py:28-29` 明确跳过 `expected_source is None` 的无答案题，所以**没有拒答指标**。
- 匹配逻辑是“相对路径或文件名 + 可选 section”（`evaluate_retrieval.py:38-43`），不检查页码和证据片段；页码/证据只在 `smoke_test_cnooc.py` 中检查。
- 数据集没有 `question_id`、`difficulty`、`category`、`expected_chunk_ids`、`answer_reference`、`requires_abstention`，也没有数据集版本/索引版本字段。
- 评测脚本不保存结果文件（`evaluate_retrieval.py` 只打印）；`smoke_test_cnooc.py` 会覆盖写 `reports/cnooc_migration_smoke.json`（`smoke_test_cnooc.py:12,50`）。

**指标口径：** 样本数 7；数据版本为当前本地 CNOOC 快照（7 份白名单、106 页、194 Chunk，HEAD `49a40df`）；证据来源为 `eval/cnooc_smoke_cases.json`；运行方式为 `evaluate_retrieval.py` / `smoke_test_cnooc.py`；本次未重跑。

### 6.3 旧模拟制度评测（不能用于当前 CNOOC）

| 数据集 | 题数 | 有答案 | 无答案 | 说明 |
|---|---:|---:|---:|---|
| `eval/legacy/retrieval_cases.json` | 7 | 6 | 1 | 旧模拟制度：年假、差旅、IT、密码安全 |
| `eval/legacy/threshold_cases.json` | 12 | 6 | 6 | 旧 Reranker 阈值校准；依赖 `answerable` 字段 |

旧 DevLog 记录的 6 题结果（`docs/devlog/001-retrieval-failure.md:122-124`、`docs/devlog/002-dataset-scale-and-evaluation.md:18-24`）：

| 指标 | Vector | Hybrid | Hybrid + Reranker |
|---|---:|---:|---:|
| Hit@1 | 83.33% | 83.33% | 100.00% |
| Hit@3 | 100.00% | 100.00% | 100.00% |
| MRR@3 | 0.9167 | 0.9167 | 1.0000 |

**指标口径：** 样本数 6 条有答案题（旧检索集共 7 条，含 1 条无答案）；数据版本为旧 4 份模拟制度文档、约 10 个 Chunk（已从 `data/` 删除，旧状态在 `.index_state/legacy_document_hashes.json`）；证据来源为 `docs/devlog/001-retrieval-failure.md:122-124` 与 `docs/devlog/002-dataset-scale-and-evaluation.md:18-24`；**不是当前 CNOOC 指标**。

这些结果基于约 4 份模拟制度文档、10 个 Chunk、6 条有答案题（`docs/devlog/002-dataset-scale-and-evaluation.md:24`），与当前 CNOOC 语料、索引和问题集不同，**不能写成当前准确率**。旧模拟文件已从 `data/` 删除，旧状态归档在 `.index_state/legacy_document_hashes.json`；历史 DevLog 保留原样。

### 6.4 历史 Smoke Test 复核

来源：`reports/cnooc_migration_smoke.json`（7 题；文件自带标签 `smoke test only, not a formal accuracy estimate`）。本次只解析既有 JSON，没有重新运行检索/重排模型。

严格匹配条件：来源路径、页码、`evidence` 片段同时匹配。

| 方法 | Top-1 严格命中 | Top-3 严格命中 | 说明 |
|---|---:|---:|---|
| Vector-only | 2/7 | 6/7 | 第 1 题 Top-1 页码错（p14 vs p6），但 Top-3 命中 |
| Hybrid | 4/7 | 6/7 | 比 Vector Top-1 好，但仍有错页/错文档 |
| Hybrid + Reranker | 4/7 | 5/7 | 用户线索的 4/7、5/7 已复核 |

**指标口径：** 样本数 7；数据版本为当前本地 CNOOC 快照（7 份白名单、106 页、194 Chunk，HEAD `49a40df`）；证据来源为 `reports/cnooc_migration_smoke.json`；本次仅解析既有 JSON，未重跑模型。

- 本次解析中，“来源 + 页码”匹配数与“来源 + 页码 + 证据”匹配数在这 7 题上相同；因为证据匹配必然意味着来源和页码匹配。
- 失败案例（`reports/cnooc_migration_report.md:31-33`）：
  1. “组织章程细则中公司的正式名称是什么？”：Reranker Top-1 为 `employee_compliance.pdf` 第 25 页，score 0.0194，正确章程页未进入 Top-3。
  2. “提名委员会负责向董事会推荐什么人选？”：Top-1 为 `nomination_committee_2025.pdf` 第 2 页，score 0.9986；指定证据在第 1 页，未进入重排 Top-3。
  3. “战略与可持续发展委员会就哪些事项向董事会提出建议？”：Top-1 为同文件第 2 页，score 0.9992；证据在第 1 页，位于重排 Top-2。
- 结论：**高 Reranker Score 不能替代逐页证据核对**；页码错位和错文档是当前最现实的质量风险。

### 6.5 数据与索引证据

| 检查 | 结果 | 方式 |
|---|---|---|
| Chroma Collection | 仅 `cnooc_knowledge`（1 个） | SQLite `mode=ro&immutable=1` |
| Chroma embeddings | 194 行 | 同上 |
| Chroma segments | 2 个（vector + metadata） | 同上 |
| Metadata 行数 | 1552 行（194 × 8 key） | 同上 |
| Metadata key | `relative_path`、`knowledge_base`、`section`、`page_start`、`page_end`、`source`、`source_url`、`chroma:document` | 同上 |
| Collection/Segment Metadata | 均为空（0 行）；未记录 Embedding 模型/索引版本 | 只读 SQLite |
| Chunk ID 一致性 | Chroma 的 `embedding_id` 集合 = 当前 `build_chunks()` 的 `chunk_id` 集合 | 只读 SQLite + `rag.build_chunks()` |
| 增量状态 | 7 条路径 → SHA-256 | `.index_state/cnooc_document_hashes.json` |
| 来源清单 | 9 行；7 份白名单哈希与原件一致 | `tests/test_cnooc_migration.py:15-24` 通过 |

**未能验证：**

- Chroma 没有记录 Embedding 模型名/版本，无法仅从数据库确认 194 条向量确实由当前 `BAAI/bge-small-zh-v1.5` 生成。
- 当前快照是本地状态；新克隆仓库没有 PDF、Chroma、状态文件，不能直接复现。
- 没有对向量内容、距离分布或索引构建时间做本次复测。

## 7. 主要风险

按影响排序（高 → 中）：

### 7.1 评测规模与口径不足（高）

- 当前只有 7 题，全部有答案；无法衡量拒答、引用准确率、Recall@K、延迟、成本。
- `evaluate_retrieval.py` 只算 Hit@1/3、MRR@3，且跳过无答案题；没有保存数据集版本、索引版本、模型版本、参数。
- 旧 6 题模拟结果与当前 CNOOC 语料不可比；不能写成当前指标。
- **影响**：后续任何“优化”都缺少可信验收标准，容易过拟合 7 题或误把 Smoke Test 当准确率。

### 7.2 检索错页/错文档（高）

- 历史 Smoke Test 中 Reranker Top-1 只有 4/7，Top-3 5/7；两个失败案例是页码错位（p2 vs p1），一个是错文档。
- 当前 PDF Chunk 是“页内切分”，同一份文件的相邻页可能语义高度相似；Reranker 可能把第 2 页排到第 1 页前面。
- RRF/BM25 没有页面感知；BM25 对“第 1 页/第 2 页”这种差异不敏感。
- **影响**：回答可能引用错误页码，企业制度问答的可信度直接受损。

### 7.3 无证据拒答仅靠 Prompt（高）

- `main.py` 只在 `results` 为空时返回固定拒答；只要检索返回任意 3 个 Chunk，就调用 LLM。
- 没有独立 Evidence Sufficiency 判断；`llm.py:18-35` 只是要求模型“资料不足时说明无法确定”。
- 当前 CNOOC 评测没有无答案题；旧阈值脚本的 12 题是模拟数据，且 `calibrate_threshold.py:43` 依赖 `answerable` 字段，当前 CNOOC 数据集没有该字段。
- **影响**：对“公司明年股价”“员工平均工资”等无答案问题，系统可能给出基于无关 Chunk 的编造答案，或过度拒答。

### 7.4 引用字段与语义支持不足（高）

- 现有 `sources` 不是凭空生成的：`main.py:13-16` 的 `source_label()` 使用检索结果的 `relative_path` 和 `page_start/page_end`；`main.py:82-86` 只保留回答中出现的 `[资料 N]` 对应的来源标签。因此“来源来自真实检索元数据”这一点成立。
- 真正缺口是返回字段不完整：`RAGResponse.sources` 是 `list[str]`，没有 Chunk ID、文档标题、`source_url`、文档版本；同一页多个 Chunk 会被合并成一个字符串标签。
- 编号映射只到来源标签，不到 Chunk ID；越界编号会被忽略，但没有逐条引用、没有 Chunk 级存在性校验，也没有“答案结论是否被该 Chunk 文本支持”的语义校验。
- 如果 LLM 不写引用，`sources` 为空；如果写了一个存在的编号但内容无关，也会被列为来源。编号/Chunk ID 存在本身不能证明结论有证据支持。
- **影响**：可以追溯到大致的文件/页码，但不能满足目标要求的 Chunk 级、逐结论可审计引用；仍需要程序化字段补全 + 语义支持校验。

### 7.5 API/LLM 异常处理薄弱（高，尤其上 API 后）

- 没有 FastAPI，因此没有 HTTP 错误码/请求校验；CLI 捕获所有异常后打印，进程仍以 0 退出（`main.py:93-96`）。
- `llm.py:8-11` 在模块导入时创建 `OpenAI` 客户端；缺少 `DEEPSEEK_API_KEY` 时可能在导入阶段失败，而不是在请求阶段返回清晰错误。
- 没有显式超时、重试、温度、最大输出 Token；`answer_with_context` 捕获所有异常并返回 `"LLM API 调用失败：..."` 字符串，调用方再把它转成 RuntimeError。
- `structured_output.py:18-49` 在导入时直接调用 API，没有 `if __name__ == "__main__"` 保护；被测试/导入时会触发外部调用。
- **影响**：未来 API 化后容易出现 500、超时、进程退出、无法重试；CLI 也无法被脚本可靠判断成功/失败。

### 7.6 增量索引与删除一致性（中高）

- `detect_changes()` 与 `index_documents.py` 的删除逻辑存在，`test_missing_selected_document...` 通过；但没有真实执行 Chroma 删除/更新。
- `upsert` 分批写入，跨批次不是原子操作；中途失败可能留下部分新 Chunk，状态文件不会保存，下一次运行可重试，但需要验证。
- BM25 在进程内从 Chroma 重建；如果服务长期运行并发生索引变更，已缓存的 `_corpus/_bm25` 不会自动刷新（`hybrid_retrieval.py:17-40`）。
- `verify_collection()` 会拒绝 `page_start < 1` 的记录（`index_documents.py:66-76`），所以未来若把 MD/TXT/DOCX 接入正式索引，当前的非 PDF Chunk 页码 0 会失败。
- **影响**：文档更新/删除后可能出现短暂或长期的不一致；需要端到端测试和运行期一致性检查。

### 7.7 PDF 表格、乱码与空页（中）

- `reports/cnooc_ingestion_audit.md` 记录 9 份 PDF、397 页：1 个空文本页、141 页带启发式警示、55 页疑似乱码、13 页文字不足；年报/ESG 的表格和乱码页风险更高。
- 当前正式索引只含 7 份合规/治理文件（106 页），这些文件的警告较少，但仍存在编号密集、表格/目录页。
- 当前 Chunking 按页内行累积约 700 字符，无法保证表头与数字列、跨页条款、双栏阅读顺序。
- **影响**：涉及金额、日期、比例、条款编号的问题可能提取错位；不能把“可提取文本”当成“语义正确”。

### 7.8 数据/索引可复现性（高）

- PDF 被 `.gitignore` 忽略；Chroma 和 `.index_state/` 也被忽略；新克隆仓库没有原件、向量库和状态文件。
- `README.md` 只有 2 行，没有安装、取数、建索引、跑评测、启动 Demo 的步骤；没有 `.env.example`。
- `requirements.txt` 固定版本，但没有说明 Python 版本、模型下载/缓存、离线运行、硬件要求。
- **影响**：P0 验收要求“新环境按 README 能启动项目”，当前无法满足；面试/演示环境重建成本高。

### 7.9 配置与可替换性不足（中）

- 模型名/Collection/路径集中在 `knowledge_config.py`，但 Top-K、候选数、RRF 常数、Chunk 大小、批量大小、阈值仍散落。
- 没有 `BaseSettings`/环境变量覆盖；`pydantic-settings` 在依赖中但未使用。
- 没有 `DocumentParser`、`EmbeddingProvider`、`VectorStore`、`KeywordRetriever`、`FusionStrategy`、`Reranker`、`LLMProvider` 的显式接口；文件级分离已有，但替换模型需要改代码。
- **影响**：实验对照和未来替换模型/存储成本较高；容易出现“改一处漏一处”。

### 7.10 权限、安全与 Prompt 注入（高，企业场景）

- Chunk Metadata 没有 ACL/租户/部门/密级字段；检索时没有权限过滤。
- 没有上传接口，因此暂无上传安全风险；但未来加 `/documents/ingest` 时必须补文件类型/大小/路径穿越校验。
- Prompt 没有明确声明“检索文档是不可信数据，不得执行其中的指令”；如果 PDF 文本含恶意指令，存在 Prompt 注入风险。
- `.env` 被忽略，但没有 `.env.example`；日志尚未实现，因此暂无日志泄密，但也没有脱敏机制。
- **影响**：当前单官方知识库可以先接受最小权限模型，但不能宣称已具备生产级权限隔离。

### 7.11 日志与可观测性缺失（中）

- 没有 request_id、阶段耗时、候选 Chunk ID、重排前后排名、Token 用量、模型版本、错误分类。
- 出问题时只能看终端打印；无法回答“为什么这题错了”“哪一步慢”“哪个候选被重排掉了”。
- **影响**：调试和回归效率低；无法支撑 P0 的可解释性要求。

### 7.12 文档与交付缺口（高）

- `README.md` 2 行；`docs/devlog/DevLog #003 — Real-world PDF Ingestion and Parsing Quality` 是 0 字节文件（`wc -l` 为 0）；`docs/devlog/readme.md` 是个人文本，不是运行说明。
- 审计当时 `AGENTS.md`、`docs/ai_workflow/`、总指导文件和本报告均未跟踪；如果当时只提交代码，GitHub 上会缺少制度、架构文档和审计报告。它们已在后续 `2bbaa9c` 中提交，当前剩余风险是 README 和环境/运行说明不足。
- **影响**：交付物不完整，评审者无法快速理解/复现项目。

## 8. 最重要的 5 个下一步任务

以下任务按推荐执行顺序排列；本次**不实施**。

| 顺序 | 任务 | 要解决的问题 | 预计涉及文件 | 验收标准 | 依赖 |
|---|---|---|---|---|---|
| 1 | **建立约 30 题 CNOOC 人工标注评测集并测当前基线** | 7 题 Smoke 全为有答案，无法衡量拒答/页码/引用/Recall | 新增 `eval/cnooc_eval_v1.json`；改 `evaluate_retrieval.py`、`smoke_test_cnooc.py`、`calibrate_threshold.py`；新增 `reports/eval/` 结果 | ≥30 题；≥5 道无答案；覆盖精确编号/数字日期金额/同义改写/相似条款/多文档；每题有 `question_id`、`difficulty`、`category`、`expected_document_ids`、`expected_pages`、`expected_chunk_ids`（可得时）、`answer_reference`、`requires_abstention`；用当前系统测 Hit@1/3、Recall@5/10、MRR、延迟；**如实际运行当前问答流程**，可把 prompt-only 拒答 precision/recall 记为“改进前基线”，并注明样本、配置、是否调用模型；未运行则不填指标，只列计划；独立证据充分性判断不在本任务验收内；保存数据集版本/索引快照/模型/参数/结果；可重复运行 | 当前 194 Chunk 快照；人工 Ground Truth；不需要重建索引 |
| 2 | **配置集中化 + request ID/阶段日志 + 结构化错误** | 模型/Top-K/RRF/Chunk/批量硬编码；无日志；LLM 客户端导入即创建；CLI 失败退出码 0 | `knowledge_config.py`（扩展或拆分 `config.py`）、新增 `logging_config.py`/`errors.py`、`llm.py`、`main.py`、`schemas.py`、`tests/` | 单一配置源覆盖模型、路径、Top-K、candidate_k、RRF k、Chunk 大小、批量、阈值、超时/重试；缺配置时清晰报错；每次查询有 `request_id`；记录 Dense/BM25/RRF/Rerank/LLM 阶段耗时与候选 ID；LLM 超时/重试；结构化错误类型；无 Key 不在导入阶段崩溃；测试用 mock 覆盖 | 无；FastAPI 的前置 |
| 3 | **证据充分性判断 + 引用校验 + 结构化 sources** | 无独立拒答；引用有编号到来源标签映射但缺 Chunk ID/标题/URL/版本与语义支持校验；Reranker 高分不等于证据正确 | `hybrid_retrieval.py`（返回分数/排名）、新增 `evidence.py`/`citation.py`、`main.py` 或 service、`schemas.py`、`llm.py`、`tests/` | 对每个问题输出 `answer` 或 `insufficient_evidence`；无证据时返回拒答且 sources 为空；引用必须映射到本次检索到的 Chunk ID；sources 至少含文档标题、路径、页码、Chunk ID、`source_url`；伪造/越界引用被拒绝；明确区分“引用存在校验”与“结论语义支持校验”，后者用人工/辅助评测，不能仅凭编号存在判定；用同一 30 题基线比较改进前后拒答与引用表现 | 任务 1（无答案题）、任务 2（配置/日志/错误） |
| 4 | **FastAPI 最小闭环** | 没有 HTTP API；P0 验收要求 API 问答；无请求/响应契约 | 新增 `app/api/`、`app/services/rag_service.py`、`schemas.py`、`requirements.txt`（增加 `fastapi`）、`tests/test_api.py` | `uvicorn` 可启动；`GET /health` 返回状态/Collection/记录数；`POST /api/v1/query` 接收 `{question, top_k?}`，返回 `answer`、结构化 `sources`、`request_id`、检索元数据；`GET /api/v1/documents` 返回已索引文档；4xx/5xx 返回 JSON 错误 + request_id；LLM/检索异常不崩溃；集成测试用 mock LLM/检索；README 有 curl 示例 | 任务 2（配置/日志/错误）、任务 3（证据/引用）；任务 1 做回归 |
| 5 | **README + `.env.example` + 本地 Demo 可复现** | README 2 行；无环境模板；PDF/Chroma 被忽略；新环境无法重建 | `README.md`、新增 `.env.example`、新增 `docs/architecture/`（架构图/运行手册）、可选 `scripts/` | 新环境按 README：创建环境 → 安装依赖 → 从官方来源取得 7 份 PDF → 配置 `DEEPSEEK_API_KEY` → `python index_documents.py` → 跑 30 题评测 → 启动 CLI/API；明确预期 7 份/106 页/194 Chunk；含架构图、已知限制、安全说明；不提交密钥/PDF/Chroma | 任务 1（评测命令）、任务 4（API 示例） |

### 8.1 最小改造顺序

```text
任务 1 评测基线
   ↓
任务 2 配置/日志/错误契约
   ↓
任务 3 证据充分性 + 引用校验
   ↓
任务 4 FastAPI 最小闭环
   ↓
任务 5 README/环境/Demo
```

**理由：**

- 先做评测，后续每一步都有同一套 Ground Truth 和指标，避免“改完不知道好坏”。
- 任务 1 的拒答指标只是当前 prompt-only 系统的改进前基线；独立证据充分性判断在任务 3，二者不能用同一验收结论。
- 配置/日志/错误契约是 FastAPI 和引用校验的共同地基；先做可以避免在 API 层重复硬编码。
- 证据/引用是回答可信度的核心；如果先包 API，会把“无拒答、无引用校验”的问题直接暴露给调用方。
- FastAPI 是包装层，不应先于核心正确性；但它是 P0 验收的必要条件，所以放在第 4。
- README/环境放在最后，是因为它要记录前面确定的命令、配置和验收结果；但它是 P0 交付的一部分，不能省略。

如果用户更看重“尽快有 API Demo”，可以把任务 4 提前到任务 3 之前做一个薄包装，但 `sources` 仍应使用任务 3 的结构化契约；否则 API 会输出不可审计的引用。

### 8.2 每项任务的边界

- 任务 1 只改评测数据/脚本/结果，不改检索算法、不重建索引；拒答指标只记录当前 prompt-only 系统的改进前基线（若实际运行），独立证据判断留给任务 3。
- 任务 2 只做配置/日志/错误契约，不改变检索排序行为。
- 任务 3 才允许改检索/生成入口的证据判断与引用结构；仍不重建索引。
- 任务 4 只做 API 包装与服务层抽取，不引入权限/上传/Docker。
- 任务 5 只做文档/环境模板/Demo，不提交 PDF/Chroma/密钥。

## 9. 最小改造方案（建议）

### Step 0：记录审计快照（不是可恢复的稳定版本）

- 审计时（2026-11-07）记录：HEAD `49a40df`、Chroma `cnooc_knowledge` 194 条、7 份 PDF/106 页、当前 7 题 Smoke 结果。
- 当时没有为这些数据创建 Commit/Tag，也没有受保护的 PDF、ChromaDB、`.index_state/` 备份；因此这只是审计快照，不是“已有可恢复的稳定版本”。
- Git 只能恢复已跟踪内容；PDF、`chroma_db/`、`.index_state/` 被 `.gitignore` 忽略，不能靠 Git 恢复。若后续需要可恢复基线，应在用户授权下另行创建 Commit/Tag 和受保护备份；本次不创建。
- 不改 BGE/Chroma/Chunker；不做索引重建。

### Step 1：评测基线（任务 1）

- 新增 `eval/cnooc_eval_v1.json`，约 30 题，至少 5 题无答案。
- 每题人工标注来源、页码、证据片段、答案参考、是否应拒答。
- 用当前系统测检索：Hit@1/3、Recall@5/10、MRR、延迟；保存结果 JSON 与运行配置。
- 拒答指标分两层：任务 1 只在**实际运行当前问答流程**时，把 prompt-only 的拒答 precision/recall 记为“改进前基线”，并注明样本、配置、是否调用模型；未运行则不填指标，只列计划。独立证据充分性判断与引用校验在任务 3 实现，并用同一评测集比较改进前后。
- 保留 `smoke_test_cnooc.py` 作为快速接线检查，但不再把它当正式指标。
- **验收门**：能在当前 194 Chunk 上重复运行，结果稳定；失败案例可定位到 Chunk/页码；能明确区分“当前系统基线”与“任务 3 改进后结果”。

### Step 2：配置/日志/错误契约（任务 2）

- 把 `TOP_K`、`CANDIDATE_K`、RRF 常数、Chunk 大小、批量、阈值、超时/重试集中到配置。
- 新增 `request_id`、阶段日志、错误类型；LLM 客户端延迟创建，补超时/重试。
- 保持检索排序与当前一致，先做“可观测”，再做“改行为”。
- **验收门**：同一问题在改动前后返回相同 Top-3（除日志/错误外无行为变化）；无 Key 时返回清晰错误。

### Step 3：证据/引用（任务 3）

- 在检索结果上增加证据充分性判断（至少：reranker score/排名 + 关键词/数字/条款命中 + 无答案题校准）。
- 生成结构化 `sources`：`document_title`、`relative_path`、`page_start`、`page_end`、`chunk_id`、`source_url`。
- 校验 LLM 引用编号必须来自本次检索结果；引用 Chunk 必须存在且文本可用；明确区分“引用存在/编号有效”和“该 Chunk 语义上支持该结论”，后者不能仅靠编号或 Chunk ID 存在来证明。
- 用同一 30 题评测集比较任务 1 的当前系统基线与任务 3 改进后结果。
- **验收门**：30 题基线中，无答案题有明确拒答；有答案题的引用可逐条回溯到 Chunk；不出现伪造来源；对“引用存在但语义不支持”的情况有单独计数/失败案例。

### Step 4：FastAPI（任务 4）

- 抽取 `RAGService`，API 只做参数校验/错误映射/序列化。
- 先实现 `/health`、`/api/v1/query`、`/api/v1/documents`；`/documents/ingest` 暂缓。
- 增加请求/响应 schema、request_id、错误码、集成测试。
- **验收门**：`uvicorn` 启动后能完成一次真实或 mock 的端到端问答；异常返回 4xx/5xx 而不是进程退出。

### Step 5：README/环境/Demo（任务 5）

- 写清楚：环境、依赖、获取 PDF、`.env`、建索引、跑评测、启动 CLI/API、已知限制。
- 新增 `.env.example`，不包含真实 Key。
- 补架构图和两条流水线说明。
- **验收门**：新环境按 README 能走到“可提问”或“可跑评测”；所有命令可复制执行。

## 10. 应暂缓的功能及原因

| 暂缓项 | 原因 |
|---|---|
| Docker / docker-compose | P1；当前没有 API，先容器化会把不稳定的接口固化；等 FastAPI 稳定后再做 |
| ACL / RBAC / 多租户 | P2；没有业务需求；需要 Metadata/索引迁移，当前单官方知识库可先预留接口 |
| Query Rewrite / 多查询 | P2；没有评测证明收益，会增加 LLM 成本和延迟；先做 30 题基线 |
| GraphRAG / Agent / LangGraph / 多模态 | P2；超出当前范围，不是 P0 交付所需 |
| OCR 与年报/ESG 入库 | 当前 7 份正式文件已够做基线；年报/ESG 表格/乱码风险高，需版面感知解析和专门评测；先不扩大语料 |
| 在 7 题上校准 Reranker 阈值 | 样本太小，容易过拟合；等 30 题基线后再校准 |
| 更换 Embedding 模型 / 重建 Chroma | 当前 BGE/194 Chunk 已验证一致，没有证据表明需要更换；重建会破坏基线 |
| 持久化 BM25 索引 | 当前从 Chroma 重建简单且一致；等 API 延迟测量后再决定 |
| 文档版本/索引版本完整管理 | P1；可先补 Metadata，再做完整版本管理；不阻塞 P0 |
| 上传接口与上传安全 | P1；没有 API 前不适用；等 `/documents/ingest` 设计时一起做 |
| Long-Context 基线 | P2 可选；成本和上下文限制需要单独设计 |
| OpenTelemetry/Langfuse 等监控平台 | 先用 Python logging；等有 API 和真实流量再评估 |
| 大规模目录重构（`app/` 全套） | 当前文件级边界够用；先做配置/服务层抽取，不为目录名搬迁代码 |

## 11. 本次实际运行的检查与测试

### 11.1 Git、目录与环境

实际运行：

```bash
pwd
git branch --show-current
git status --porcelain=v1
git log --oneline -15
git tag --sort=-creatordate
git diff --stat
git diff --cached --stat
git log -1 --format='%H%n%ad%n%s'
conda run -n agent python -V
conda run -n agent python -c "import chromadb, pypdf, sentence_transformers, rank_bm25, jieba, pydantic; print('chromadb', chromadb.__version__); print('pypdf', pypdf.__version__); print('pydantic', pydantic.__version__)"
conda run -n agent python -c "import importlib.util as u; print('fastapi installed:', bool(u.find_spec('fastapi')))"
```

结果（审计当时，2026-11-07）：

- 仓库路径：`/Users/luogewen/Documents/GitHub/enterprise-knowledge-agent`
- 审计当时分支：`main`；HEAD：`49a40dfdf00d60075cf5bfdbfd1a9f5071982cf8`；本地 `origin/main` 同值；无 Tag。
- 审计当时未跟踪：`.DS_Store`、`AGENTS.md`、`data/.DS_Store`、`data/cnooc/.DS_Store`、`docs/ai_workflow/`、`docs/enterprise_rag_architecture_development_guide.md`。
- 审计当时 `git diff --stat` 与 `git diff --cached --stat` 均为空。
- Python：3.12.14；`chromadb 1.5.9`、`pypdf 6.20.1`、`pydantic 2.13.5`；`fastapi installed: False`。
- `requirements.txt`：有 `uvicorn==0.54.0`、`pydantic-settings==2.15.0`、OpenTelemetry 包；无 `fastapi`。
- 生产代码 `grep`：未发现 `FastAPI`、`APIRouter`、`request_id`、`logging.`/`logger`；仅 `tests/test_ingestion.py:14` 设置 `pypdf` 日志级别。
- 2026-11-08 修订时 HEAD 已为 `2bbaa9c`，具体状态见 11.6。

### 11.2 只读数据核对

实际使用：

```python
import sqlite3
con = sqlite3.connect('file:chroma_db/chroma.sqlite3?mode=ro&immutable=1', uri=True)
# 查询 collections / segments / embeddings / embedding_metadata
```

结果：

- Collections：1 个，`cnooc_knowledge`。
- Segments：2 个（vector + metadata）。
- Embeddings：194 行。
- Embedding Metadata：1552 行；8 个 key。
- Collection Metadata / Segment Metadata：均为空（0 行）。
- Chroma `embedding_id` 集合与当前 `rag.build_chunks()` 的 `chunk_id` 集合完全相等。
- `.index_state/cnooc_document_hashes.json`：7 条。
- `data/cnooc/sources.csv`：9 行；7 份白名单哈希与原件一致（测试验证）。

另用只读 Python 调用 `rag.build_chunks()`：

- 194 个 Chunk；194 个唯一 ID。
- 每份文档 Chunk 数：43 / 29 / 89 / 4 / 18 / 7 / 4。
- `page_start < 1` 或 `page_end != page_start` 的数量：0。

### 11.3 实际运行的测试

以下命令均在 `conda activate agent` 后运行（Python 3.12.14），并设置 `PYTHONDONTWRITEBYTECODE=1`。

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test_ingestion.py' -v
```

结果：`Ran 4 tests in 13.655s`，`OK`。

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test_cnooc_migration.py' \
  -k test_allowlist -k test_chunks -k test_state -k test_missing -v
```

结果：`Ran 4 tests in 0.869s`，`OK`。

合计：9 个测试中实际运行 8 个，全部通过；1 个未运行（见下）。

### 11.4 未运行项及原因

| 未运行项 | 原因 |
|---|---|
| `test_cnooc_migration.py::test_bm25_and_vector_use_identical_ids` | 会打开 Chroma `PersistentClient`，可能写 SQLite/WAL；为避免改动受保护数据库，未运行；已用 `mode=ro&immutable=1` 只读查询做 ID 等价核对 |
| `python index_documents.py` | 会写 Chroma 和 `.index_state/`；本次禁止重建/写入索引 |
| `python main.py` | 会调用 DeepSeek API；本次禁止调用 API |
| `python smoke_test_cnooc.py` | 会加载 BGE/Reranker 并覆盖写 `reports/cnooc_migration_smoke.json`；本次禁止模型推理和报告写入 |
| `python evaluate_retrieval.py --dataset ...` | 会加载 BGE/Reranker；本次只解析既有结果，不重新计算 |
| `python calibrate_threshold.py --dataset ... --output ...` | 会加载 Reranker 并写输出；且当前 CNOOC 数据集缺 `answerable` 字段 |
| `python structured_output.py` | 导入即调用 DeepSeek API；本次禁止 API 调用 |
| `git fetch` / 远端 Tag 核对 | 未联网；只核对本地引用 |

### 11.5 受保护文件状态

- 审计期间未修改业务代码、PDF、`sources.csv`、ChromaDB、`.index_state/`、`eval/`、`requirements.txt`、`.env`。
- 审计当时 `git status` 除本任务新增的审计报告外，未跟踪文件集合未变化；已跟踪文件无改动，暂存区为空。
- 只读 SQLite 使用 `immutable=1`，未写入 Chroma；未读取 `.env` 内容。
- `chroma_db/chroma.sqlite3` 的 mtime 为 `Nov 7 15:46:37 2026`，早于本次审计开始时间；`.index_state/cnooc_document_hashes.json` 为 `Oct 29 19:18:03 2026`；`data/cnooc/sources.csv` 为 `Oct 23 23:25:20 2026`。未见审计期间变更。

### 11.6 2026-11-08 修订轮次的检查与 Git 状态

- 修订开始时 HEAD：`2bbaa9c`（`创建prompt 管理`），本地 `origin/main` 同值；审计当时的 `49a40df` 已不再是 HEAD。
- Prompt 差异核对：DeepSeek 报告已将归档版与其可见的完整聊天指令按段落比较；差异主要是标题层级、措辞、Markdown 格式及重复段落，未报告任务目标、范围或边界的实质冲突。但实际聊天版全文未写入仓库，故只完成差异说明，未完成逐字归档。详见 `docs/ai_workflow/issues/RAG-20261107-002-ISSUE-01.md`。
- 文档内部链接：本报告及同 Task ID 的执行记录、ISSUE-01、任务索引、开发流水账相对链接失效 0 处。
- 行号引用：检查报告中的 64 处 `文件:行号` 引用，越界 0；检查中把 `knowledge_config.py` 的 15–35 行引用修正为 15–33 行（实际文件 33 行）。
- `git diff --check`：无空白错误。
- 本轮未运行索引、模型推理、检索评测或 RAG 单元测试；未修改业务代码、测试、评测数据、知识库、索引、依赖或 `.env`；未 Commit/Tag/Push。
- 本轮修改/新增：审计报告、执行记录、ISSUE-01、任务索引、开发流水账；其中 ISSUE-01 与 `prompts/architecture/RAG-20261107-002_audit_report_revision.md` 为未跟踪文件，其余为已跟踪文件的未提交修改。

## 12. 未验证的假设

1. **历史 Smoke Test 结果可代表当前模型行为**：不成立为“本次实测”。本次只解析既有 JSON，没有重新运行 BGE/Reranker；模型缓存、依赖版本或硬件变化都可能改变结果。
2. **当前 Chroma 向量由 `BAAI/bge-small-zh-v1.5` 生成**：代码和迁移报告这样写，但 Chroma 不记录 Embedding 模型/版本；未从数据库验证。
3. **历史索引运行（194 Chunk、首次 50.6 秒、第二次 0.2 秒）仍可复现**：本次未运行 `index_documents.py`；当前快照可能来自历史运行。
4. **Chunk ID 在当前代码下稳定**：本次用当前代码重新切块得到 194 个 ID，且与 Chroma 一致；但没有验证不同 `pypdf` 版本/解析器下的稳定性。
5. **BM25 与 Chroma 文本完全一致**：代码从 Chroma 读取，结构上一致；本次只核对了 ID 集合，没有运行 BM25 或比较全部文本。
6. **RRF/Reranker 的实际排序**：本次只读代码；历史 Smoke 有结果，但未重跑。
7. **文档删除/更新端到端可用**：只验证了 `detect_changes()` 的删除检测；没有真实执行 Chroma 删除/更新。
8. **PDF 文本/表格质量**：本次没有做视觉对照；`reports/cnooc_ingestion_audit.md` 是 2026-10-24 的启发式审计，不等于逐页人工校验。
9. **DeepSeek `deepseek-flash` 可用**：历史报告记录一次成功；本次未读取 `.env`、未调用 API，无法确认当前 Key/模型状态。
10. **远端 Git 状态**：未 `git fetch`；只确认本地 `origin/main` 引用与 HEAD 同值，远端实时状态未知。
11. **FastAPI 不存在**：通过文件检查和 `fastapi installed: False` 确认；不排除仓库外有未接入的代码。
12. **当前 7 题 Smoke 的“严格命中”可外推**：不能；7 题不是正式准确率，且全部为有答案题。

## 13. 审计结论与等待确认

- 当前项目是一个**可运行的 CNOOC 单知识库 RAG 原型**：离线入库、Chunk 元数据、SHA-256 增量检测、Chroma 向量检索、BM25、RRF、Cross-Encoder Reranker、DeepSeek 生成和来源页码输出都已存在。
- 但它还不是总指导所要求的**企业级可交付应用**：缺少 FastAPI、日志/request ID、独立证据充分性判断、Chunk 级引用字段与语义支持校验、权限、Docker、配置集中化、约 30 题评测集和可复现 README。
- 历史线索中的 7 份 PDF/106 页/194 Chunk/`cnooc_knowledge` 已与当前本地快照核对一致；Reranker Smoke Top-1 4/7、Top-3 5/7 已从既有 JSON 复核，但**不是本次实测准确率**。
- 建议先按第 8 节的 1 → 2 → 3 → 4 → 5 顺序推进；本次不实施任何任务。
- **等待用户确认优先级后**，再按总指导 P0 → P1 → P2 推进。审计任务到此停止，不扩大为 FastAPI 开发或架构重构。

---

**本次报告状态：已写入仓库，尚未 Commit/Tag/Push。**
