# RAG-20261108-002：搭建企业 RAG 最小可运行应用骨架

你在 `enterprise-knowledge-agent` 仓库执行 Task ID `RAG-20261108-002`。本条消息全文是实际交给你的 Prompt；仓库内的同名文件应与收到的文字一致，若有差异，先将实际收到的完整版本另存并说明，不要用摘要代替。此次目标是把已有的 CNOOC RAG 脚本组成**可启动、可测试的本地应用闭环**，不是新建一批空目录，也不是宣称已完成企业级安全或正式评测。完成后停止，交由用户和 Codex 验收。

## 先检查

先读用户编写的总指导 `docs/enterprise_rag_architecture_development_guide.md`（重点第 4、6、7、11、12 节）、`AGENTS.md`、`docs/ai_workflow/README.md`、当前任务记录、`main.py`、`llm.py`、`schemas.py`、`knowledge_config.py`、`retrieval.py`、`hybrid_retrieval.py`、`index_documents.py`、现有测试和 README。检查 `git status`、HEAD、依赖和当前运行入口，保护用户未提交的修改。`RAG-20261108-001` 评测任务已暂缓，本次不顺带执行。

## 本次实现：一个纵向闭环

1. 从 `main.py` 提取一条可复用的问答服务路径：输入问题和 `top_k`，依次调用现有 Hybrid/RRF/Reranker、构造 Context、调用 LLM、返回答案和来源。CLI 与 API 调用**同一服务**，不要复制两套业务逻辑。默认仍为 Top-3、候选 5；不改变现有检索排序、Chunk、索引或 Prompt 的事实回答规则。检索和 LLM 依赖应可注入或替换，便于离线测试。
2. 建立最小 FastAPI 应用：`GET /health` 只表示进程存活，启动/健康检查不得加载模型或要求 API Key；`POST /api/v1/query` 接受非空 `question` 和有边界的 `top_k`，返回 `answer`、由**本次检索结果元数据**生成的 `sources`、`request_id`；`GET /api/v1/documents` 只读返回当前**实际已索引**文档的基本信息，索引不存在时清晰报错，不把白名单误写成“已索引”。接口用 Pydantic 模型定义和校验。保留旧 CLI 的可用性；若响应字段需要扩展，说明兼容策略。
3. 做最小配置和可靠性处理：集中本次用到的模型名、Collection、路径、Top-K、候选数、超时和日志级别；尽量复用 `knowledge_config.py`，不要出现两个互相矛盾的配置源。修复 `llm.py` 在导入时创建客户端的问题，缺少 `DEEPSEEK_API_KEY` 时应在真正调用 LLM 时给出明确错误；API 错误返回稳定 JSON 和 `request_id`，不把密钥、完整原文或内部堆栈暴露给调用方。记录各阶段耗时和 request ID，但默认不记录完整问题、Context 或密钥。
4. 补最小运行文档：README 写明创建环境、安装依赖、准备被 Git 忽略的 CNOOC PDF/Chroma 数据、启动 API、调用三个端点及运行测试的实际命令；新增不含真实密钥的 `.env.example`。如果需要 FastAPI，只在 `requirements.txt` 添加经当前环境验证的兼容依赖，不整体刷新依赖文件。说明当前是本地单用户原型，权限、上传、Docker、正式评测及更严格的证据校验尚未完成。

## 验收与测试

- 使用 mock 检索器和 mock LLM 测试服务及 API：正常回答、无检索结果、缺 Key/模型或索引、LLM 失败、非法/过长问题、`top_k` 边界、来源必须来自本次检索结果、CLI 与服务结果一致。测试不得调用 DeepSeek API 或写生产 Chroma。
- 实际启动应用并请求 `/health`；在不具备本地 PDF、Chroma 或 Key 的环境中，健康检查仍应成功，查询/文档接口应给出清晰的未就绪错误。若本机条件允许，可验证真实索引的只读 `/documents`；**不要为测试重建索引**。没有实际运行的端到端 DeepSeek 问答必须标为“未验证”，不能把 mock 测试说成真实 API 回答成功。
- 对照修改前后默认 CLI 参数和返回来源，确认默认行为未被无意改变。运行相关旧测试、新测试和 `git diff --check`，记录准确命令、通过/失败数与未运行项。

## 修改边界与记录

允许新增最少必要的应用/服务/配置模块和 API 测试，修改 `main.py`、`llm.py`、`schemas.py`、`knowledge_config.py`、`README.md`、`.env.example`、`requirements.txt` 以及本 Task ID 的管理记录。文件布局可依据现有项目选择，但要保持职责清楚。不要修改原始 PDF、`sources.csv`、ChromaDB Collection、`.index_state/`、评测数据、生产检索/RRF/Reranker 算法或上一任务的审计报告；不要运行 `index_documents.py`、重新计算文档 Embedding、开展 30 题评测或增加 ACL/Docker/上传功能。若确需越界，先说明原因并停止该部分。不要 Commit、Tag 或 Push。

在 `docs/ai_workflow/execution_logs/RAG-20261108-002.md` 追加实际执行轮次，记录改动文件、测试、运行命令、Git Diff、已验证与未验证的能力；更新任务索引和开发日志。最后用中文说明应用怎么启动、哪些端点真实测试过、还缺什么，以及下一步如何继续完善。完成后停止，不自动转去评测任务。
