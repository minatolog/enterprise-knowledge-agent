<!--
Task ID: RAG-20261107-002
接收日期: 2026-11-07 (Australia/Sydney)
来源: Codex 根据用户“根据现在的依据、总架构和目前进度，给我一个交给 DeepSeek 的 Prompt”编写；正文是拟交给 DeepSeek 的完整任务指令，并非用户逐字原文。
记录范围: 完整拟执行 Prompt。用户的原始请求保存在下方“任务来源”元数据中；DeepSeek 的实际执行尚未发生。
执行记录: ../../execution_logs/RAG-20261107-002.md
-->

# RAG-20261107-002：审计当前 RAG 架构，给出下一阶段开发顺序

你是 `enterprise-knowledge-agent` 项目的**只读架构审计员**。本次只核对现状并产出报告，不开发新功能。技术目标和阶段路线以用户编写的 `docs/enterprise_rag_architecture_development_guide.md` 为总指导；AI 记录流程遵循根目录 `AGENTS.md` 和 `docs/ai_workflow/README.md`。当前代码与 Git 状态是“已经实现什么”的证据，架构指导中的目标不能写成已完成。

## 开始条件

先确认你确实能读取当前项目仓库和上述总指导文件。如果你在 DeepSeek 网页版、无法访问本机路径或缺少文件，请**停止实证审计**，列出需要我提供的文件/仓库访问方式；不要假装已经打开文件、运行代码或检查 Git。不要要求我上传 `.env`、API Key、ChromaDB 数据库或模型权重。

若能访问仓库，继续沿用 Task ID `RAG-20261107-002`。开始前阅读总指导的第 1、3、4、5、6、8、10、11、14、15 节，查看 `AGENTS.md`、`docs/ai_workflow/TASK_INDEX.md`、本 Prompt、现有报告和开发日志，并检查 `git status`、当前分支、最近 Commit 和 Tag。保护所有未提交文件。

## 已知历史线索（必须重新核实）

此前记录为：中海油 CNOOC 官方资料；正式 Collection `cnooc_knowledge`；白名单 7 份 PDF、106 页、194 个 Chunk；另有年报和 ESG PDF 未入正式索引。技术链路曾为逐页 PDF 解析与分块 → SHA-256 增量索引 → BGE Embedding + ChromaDB → BM25 + 向量检索 → RRF → Cross-Encoder Reranker → DeepSeek 回答并列来源与页码。迁移报告记录过 7 题 Smoke Test，严格按来源、页码和证据匹配时 Reranker Top-1 为 4/7、Top-3 为 5/7；这不是正式准确率。最近可见代码 Commit 曾是 `49a40df`。这些都是**线索，不是你本次的实测结论**。

## 审计范围

1. 列出当前真实目录结构和代码入口；逐个核对 `knowledge_config.py`、`ingestion.py`、`rag.py`、`document_tracker.py`、`index_documents.py`、`retrieval.py`、`hybrid_retrieval.py`、`main.py`、`llm.py`、`schemas.py`、`evaluate_retrieval.py`、`smoke_test_cnooc.py`、`tests/`、`eval/`、`reports/` 与现有文档。不存在的文件要写“不存在”。
2. 画清当前**离线入库**与**在线问答**数据流，说明每一步的输入、输出、负责文件，以及哪些地方保留来源、页码和 Chunk ID；区分 BM25、Chroma、RRF、Reranker 和 LLM 的职责。
3. 对照总指导的 P0/P1/P2 和目标架构，逐项标记“已实现且本次验证”“代码存在但未验证”“仅历史报告记录”“未实现”。尤其核对 FastAPI、日志、证据充分性判断、引用校验、权限、Docker、配置集中化和评测集规模；不要因为依赖表里有包就认定功能已实现。
4. 检查测试覆盖与历史评测口径；区分模拟制度旧评测和当前 CNOOC 评测。分析数据一致性、增量索引、文档删除、PDF 表格/乱码、检索错页、无证据拒答、引用和 API 异常风险。任何指标都写清样本数、数据版本和证据来源。
5. 给出**优先级最高的 5 个下一步任务**，每项说明解决什么问题、预计涉及哪些文件、验收标准和依赖关系。提出最小改造顺序，并列出应暂缓的技术及原因。不要在这次审计中实施这些任务。

## 操作边界与证据

- 可以读代码、文档、Git 元数据和已有报告；本地数据库若要核对，只能使用确认不会写入的只读方式。测试仅在确认不会改动受保护数据时运行，且必须记录准确命令和结果；未运行就写“未运行”。
- 不修改业务代码、PDF、`sources.csv`、ChromaDB、`.index_state/`、评测数据、依赖或 `.env`；不重建索引、不计算新 Embedding、不调用 DeepSeek API，不执行 Commit、Tag 或 Push。
- 每条关键结论尽量引用仓库相对路径与行号或实际命令输出。遇到总指导与代码不一致，列为“目标与现状差距”，不擅自改代码或改写总指导。

## 交付

若有仓库写入能力，只新增 `reports/RAG-20261107-002_architecture_audit.md`，并在同一 Task ID 的 `docs/ai_workflow/execution_logs/RAG-20261107-002.md` 追加你的实际执行轮次、工具/模型、命令、结果、未解决事项，更新 `TASK_INDEX.md` 与 `DEVELOPMENT_LOG.md` 的状态。若没有写入能力，在聊天中输出可保存的 Markdown，并明确标记“尚未写入仓库”。

报告至少包含：真实目录结构；两条流水线及文件映射；目标与现状对照表；测试/评测证据和缺口；数据一致性、增量索引、引用、异常处理风险；最重要的 5 个待办；最小改造方案；应暂缓的功能。末尾单列“本次实际运行的检查与测试”以及“未验证的假设”。

完成审计后**停止**，等待我确认优先级，再按总指导的 P0 → P1 → P2 推进。不要把审计任务扩大成 FastAPI 开发或架构重构。

<!-- 任务来源（用户原文）：好 根据现在的依据 总架构 和目前的进度 给我一个交给deepseek的prompt -->
