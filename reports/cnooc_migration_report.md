# CNOOC 单一知识库迁移验收

验收日期：2026-10-29。正式数据源是 `knowledge_config.py` 中明确列出的 7 份中国海洋石油有限公司合规及治理 PDF。2025 年年报与 ESG 报告继续保留在 `data/cnooc/`，本次没有索引。

## 迁移结果与索引

正式 Chroma Collection 为 `cnooc_knowledge`，持久化目录仍为 `chroma_db/`，Embedding 仍为 `BAAI/bge-small-zh-v1.5`。旧 `enterprise_knowledge` Collection 的 10 条模拟记录在新索引和端到端问答验证后删除；其不再被 SQLite segment 引用的旧向量文件目录也已清理。目前只剩 `cnooc_knowledge`，实际记录数为 194。BM25 从该 Collection 的相同 194 条文档和 Chunk ID 构建，不再单独扫描 `data/`。七份文件共 106 个 PDF 页，生成 194 个非空、唯一 ID 的 Chunk；首次索引耗时 50.6 秒（其中模型尝试访问 Hugging Face 后使用本地缓存），第二次不变文件重跑耗时 0.2 秒，记录数仍为 194。没有解析失败或跳过的正式文件。

| 文档 | 页数 | Chunk 数 |
|---|---:|---:|
| `compliance/employee_compliance.pdf` | 27 | 43 |
| `compliance/director_ethics_2026.pdf` | 16 | 29 |
| `governance/articles_2025.pdf` | 43 | 89 |
| `governance/nomination_committee_2025.pdf` | 3 | 4 |
| `governance/audit_committee.pdf` | 10 | 18 |
| `governance/remuneration_committee.pdf` | 4 | 7 |
| `governance/strategy_sustainability_committee.pdf` | 3 | 4 |

每个 Chunk 的 ID 包含原始相对路径、PDF 页码和该页的顺序号；Metadata 含 `source`、`relative_path`、`knowledge_base`、`page_start`、`page_end`、`section` 与官方 `source_url`。目前按页分块，所以每个 Chunk 的起止页相同；没有将物理页号伪装成业务章节。页内按提取行尽量在约 700 字符附近切分，长行才退回字符切分。已有 Markdown/TXT/DOCX 通用读取能力保留。

## 检索与问答验证

`eval/cnooc_smoke_cases.json` 的 7 道题均由原 PDF 指定页中的短证据支持。对 Vector-only、Hybrid 和 Hybrid + Reranker 实际运行，详细候选见 `reports/cnooc_migration_smoke.json`。严格要求“来源、页码和证据片段同时匹配”时，Top-1 分别为 2、4、4 道；Top-3 分别为 6、6、5 道。这只是小型接线检查，**不是正式准确率评测**。

| 问题 | Reranker Top-1 | 页码 | Score | 指定证据在该 Chunk 中？ |
|---|---|---:|---:|---|
| 员工入职时需要签署什么合规文件？ | `employee_compliance.pdf` | 6 | 0.9843 | 是 |
| 董事及高级管理人员应如何处理利益冲突？ | `director_ethics_2026.pdf` | 8 | 0.9992 | 是 |
| 审核委员会的宗旨包括监督哪些事项？ | `audit_committee.pdf` | 1 | 0.9020 | 是 |
| 薪酬委员会负责审查和批准谁的薪酬方案？ | `remuneration_committee.pdf` | 1 | 0.9756 | 是 |
| 组织章程细则中公司的正式名称是什么？ | `employee_compliance.pdf` | 25 | 0.0194 | 否；问题过于通用，正确章程页未进入 Top-3 |
| 提名委员会负责向董事会推荐什么人选？ | `nomination_committee_2025.pdf` | 2 | 0.9986 | 否；指定证据在第 1 页，未进入重排 Top-3 |
| 战略与可持续发展委员会就哪些事项向董事会提出建议？ | `strategy_sustainability_committee.pdf` | 2 | 0.9992 | 否；指定证据在第 1 页，位于重排 Top-2 |

上述后三例说明高 Reranker Score 和正确文件名都不能替代逐页证据核对。用原模拟制度的年假、密码锁定、酒店上限三类问题再次检索，Vector、Hybrid、Reranker 的返回来源全是 CNOOC PDF；这证明旧模拟记录不再返回，但不能证明这些问题在 CNOOC 文档中有答案。

DeepSeek 端到端调用成功一次。问题是“员工入职时需要签署什么合规文件？”，检索 Top-1 为合规手册第 6 页，最终 Pydantic 输出提及《合规承诺书》、保密协议，并只列出答案明确标注的第 6、10、14 页来源。这些内容与对应 PDF 页的提取文本一致。首次在沙盒内连接失败，经允许在沙盒外重试后成功；未进行批量付费调用。该单例不能证明所有问题都能拒答或正确引用。

## 实际代码和数据变更

- 新增 `knowledge_config.py`：统一 Collection、模型、状态路径和精确 7 文件白名单。
- 修改 `rag.py`：对 PDF 逐页切块，保留路径、页码、知识库、稳定 Chunk ID；默认 `build_chunks()` 只使用白名单。
- 修改 `document_tracker.py`：只对当前白名单中存在的文件计算 SHA-256，使用独立的 CNOOC 状态文件；缺失文件进入删除变更。
- 修改 `index_documents.py`：校验 `sources.csv` 中的原件哈希，增量写入新 Collection，按文档清除失效 Chunk，写后核对并仅在成功后保存新状态。
- 修改 `retrieval.py`、`hybrid_retrieval.py`：向量与 BM25 使用同一个 CNOOC Collection 的记录和 Chunk ID；RRF 按 ID 去重，保留原有 RRF 公式和 Reranker 模型。
- 修改 `main.py`、`llm.py`：检索结果和上下文显示文件相对路径与实际 PDF 页码；最终 `sources` 只列出模型答案中明确引用的资料编号。保留现有 DeepSeek 调用和 Pydantic 输出。
- 旧评测 JSON 移入 `eval/legacy/`；`evaluate_retrieval.py` 和 `calibrate_threshold.py` 现在要求显式传入数据集，避免默认把模拟题当作 CNOOC 评测。新增 7 道有原页证据的 Smoke Test。
- 新增 `tests/test_cnooc_migration.py`，旧解析测试继续保留。四份模拟制度从正式 `data/` 中删除，已在 Git 历史中可恢复。旧 SHA 状态归档为 `.index_state/legacy_document_hashes.json`，正式状态为 `.index_state/cnooc_document_hashes.json`。历史 DevLog 未改。

## Git 与原件安全

九份 PDF 的 SHA-256 与 `sources.csv` 均一致，本地原件仍在。`.gitignore` 新增精确规则 `data/cnooc/**/*.pdf`；九份 PDF 已通过 `git rm --cached` 从当前 Git 索引移除，**本地文件未删除**。这九份 PDF 在本次操作前已经位于 `origin/main` 的历史提交 `b2a076a`，因此本次操作只能阻止后续提交继续跟踪，不能撤销历史公开版本。`sources.csv` 保持可跟踪。`.env`、Chroma 和状态目录仍被忽略。没有自动 Commit 或 Push。新克隆的仓库不会包含原始 PDF，需要从官方来源自行取得本地副本后才可重建索引。

## 执行的验证与剩余风险

- `python index_documents.py`：7 份文档、194 Chunk，首次成功；第二次运行仍为 194。
- `python smoke_test_cnooc.py`：七题分别运行 Vector、Hybrid、Reranker；具体未命中已保留在 JSON。
- `python main.py`：一次真实 DeepSeek 问答成功，结构化输出和页码来源可用。
- `python -m unittest discover -s tests -v`：迁移与解析测试通过。
- Collection 核对：仅 `cnooc_knowledge`，194 条；BM25 ID 集合与 Chroma ID 集合完全相同。

仍需注意：年报、ESG 报告的表格与乱码页尚未索引；页内行切分仍不能保证复杂条款或表格的布局语义；对无证据问题目前依赖提示词拒答，没有独立 Evidence Sufficiency 检查；七题 Smoke Test 太小，不能据此宣称正式检索准确率。以后若要改善，应先做更完整的真实证据评测，再处理难检索条款与版面感知切块，最后决定是否纳入年报和 ESG。
