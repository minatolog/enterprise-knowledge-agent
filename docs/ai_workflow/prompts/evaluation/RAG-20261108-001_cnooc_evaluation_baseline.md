# RAG-20261108-001：建立 CNOOC 检索评测集与可复现基线

你在 `enterprise-knowledge-agent` 仓库执行 P0 评测任务，Task ID 为 `RAG-20261108-001`。本条消息全文就是本次实际交给你的 Prompt；执行前将它原样保存在 `docs/ai_workflow/prompts/evaluation/RAG-20261108-001_cnooc_evaluation_baseline.md`，不要用摘要替代。执行工具和模型按你实际使用的填写。完成后停止，等用户和 Codex 验收。

## 背景与开始检查

用户编写的 `docs/enterprise_rag_architecture_development_guide.md` 是总架构指导，重点阅读第 8、11、12、15 节；再读 `AGENTS.md`、`docs/ai_workflow/README.md`、`reports/RAG-20261107-002_architecture_audit.md`、`docs/ai_workflow/TASK_INDEX.md` 和本任务执行记录。先检查 Git 状态并保护所有未提交改动；上一任务 `RAG-20261107-002` 仍为 REVIEW，相关文件不得被覆盖、重置或顺带提交。

实际代码和数据优先于历史报告。检查 `eval/cnooc_smoke_cases.json`、`eval/legacy/`、`evaluate_retrieval.py`、`smoke_test_cnooc.py`、`calibrate_threshold.py`、`retrieval.py`、`hybrid_retrieval.py`、`knowledge_config.py`、`rag.py`、`data/cnooc/sources.csv` 和当前正式索引。历史线索为 7 份白名单 PDF、106 页、194 Chunk、Collection `cnooc_knowledge`；必须重新核实，不把旧模拟制度或 7 题 Smoke 当正式评测。

## 本次目标

1. 建立 `eval/cnooc_eval_v1.json`：约 30 道有效题，至少 5 道“在当前正式索引的 7 份文件中无答案”的题；有答案题覆盖全部 7 份文件及条款编号、同义改写、数字/日期/金额、相似条款干扰和多文档证据。每题记录 `question_id`、`question`、`difficulty`、`category`、`expected_document_ids`、`expected_pages`、适用时的 `expected_chunk_ids`、简短 `evidence`、`answer_reference`、`requires_abstention`、`review_status`。多处正确证据用列表记录。无答案题写明核查的语料范围和判断依据；证据不足或含糊的题先剔除或标记待复核，不纳入正式分母。既有 7 题可以参考，但必须重新核对 PDF 原文、页码和 Chunk，不能直接复制旧标签。
2. 对每个有答案题核对原始 PDF 的对应页、短证据片段与当前 Chunk ID；不能从检索算法的输出反推 Ground Truth。AI 制作的标签须标为 `ai_draft`，另生成便于用户逐题审阅的清单；未经用户确认，不得称“人工标注已验收”或把结果称为正式准确率。
3. 扩展或新增独立评测脚本，在同一数据集、同一索引快照和明确的候选预算下比较 Dense、BM25、Hybrid/RRF、Hybrid/RRF+Reranker。计算适用的 Hit@1、Hit@3、Recall@5、Recall@10、MRR；Hit 与 Recall 分开定义，多证据题按相关 Chunk 集合计算 Recall。若某方法实际只返回 3 或 5 个结果，不得伪造 @10；可以在评测调用层显式请求足够候选并记录配置，不改生产排序逻辑。当前 CLI 的 Top-3/candidate-5 行为与扩展 Top-10 评测若不同，分别标清。
4. 保存逐题、逐方法的候选 Chunk ID、来源、页码、排名、分数（可得时）、是否命中和失败原因；另保存汇总 JSON 与 Markdown 报告，包含数据集版本/哈希、PDF 或索引快照标识、Collection 数量、模型标识、参数、运行命令、运行环境、实际耗时及 P50/P95（若测量）。无答案题不混入有答案检索指标分母，单独统计和分析。当前系统没有独立证据充分性判断；本任务不实现它，也不调用 DeepSeek API，因此不填写答案正确率或拒答 precision/recall 的实测值。
5. 增加少量有意义的测试，覆盖数据集结构、重复题 ID、相关集合与页码合法性、Hit/Recall/MRR 的计算和无答案题分母；执行测试及一次可复现的本地评测。若模型或索引缺失，记录阻塞与已完成部分，不制造指标。

## 边界与交付

允许修改评测数据/脚本、直接相关测试、`reports/eval/` 下的结果和本 Task ID 的 Prompt/执行记录/任务索引/开发流水账。`smoke_test_cnooc.py`、`calibrate_threshold.py` 只有确需兼容新数据格式时才修改；旧 `eval/legacy/` 和历史报告保持原样。不要修改生产检索、RRF、Reranker、生成、索引或 API 代码，不重建索引、不重新计算文档 Embedding、不改原始 PDF、`sources.csv`、ChromaDB Collection、`.index_state/`、依赖或 `.env`。评测若需通过可能写库的 `PersistentClient` 读取 Chroma，请先用隔离副本或确认安全的只读方式，不能写生产库；模型不可用时停止实测并说明。不要调用 DeepSeek API，不 Commit、Tag 或 Push。若必须越过上述范围才能完成，先说明原因并停止该部分。

执行后在 `docs/ai_workflow/execution_logs/RAG-20261108-001.md` 记录实际工具/模型、改动文件、命令、测试、结果、失败题、限制和 Git Diff；更新 `TASK_INDEX.md` 与 `DEVELOPMENT_LOG.md`。报告必须区分“AI 草拟、来源已核对、用户已复核”的标签状态与“实测、历史记录、未运行”的指标状态。最后用中文给出已完成内容、真实指标及分母、不能验证的部分和下一步人工审阅清单，然后停止。
