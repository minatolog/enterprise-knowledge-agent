# enterprise-knowledge-agent

基于 CNOOC 官方资料的企业知识库 RAG 本地原型。当前实现离线入库、Chroma 向量检索、BM25、RRF、Cross-Encoder Reranker、DeepSeek 生成，并提供共享服务层的 CLI、FastAPI 与本地对话测试页面。

> 当前是本地单用户原型，不是生产系统。权限/ACL、上传、Docker、正式评测和严格的证据/引用语义校验尚未完成。

## 架构

- `app/service.py`：`RAGService`，CLI 和 API 共用；输入问题与 `top_k`，返回答案、结构化 sources、`request_id` 和阶段耗时。
- `app/api.py`：FastAPI 路由 `/health`、`/api/v1/query`、`/api/v1/documents`。
- `app/web/`：由 FastAPI 同源提供的本地网页，调用现有问答与文档接口。
- `app/index_status.py`：只读 SQLite 检查实际索引；不写 Chroma。
- `knowledge_config.py`：共享配置（模型、路径、Top-K、候选数、超时、日志级别）。
- `retrieval.py` / `hybrid_retrieval.py`：现有向量/BM25/RRF/Reranker 链路，未改排序算法。
- `llm.py`：延迟创建 DeepSeek 客户端；缺 Key 在真正调用时给出明确错误。
- `main.py`：旧 CLI，使用同一个 `RAGService`。
- `schemas.py`：CLI 兼容的 `RAGResponse` 与 API Pydantic 模型。

## 环境

Python 3.12（当前验证 3.12.14）。

```bash
conda create -n agent python=3.12 -y
conda activate agent
python -m pip install -r requirements.txt
```

## 准备数据（PDF/Chroma 被 Git 忽略）

仓库不包含原始 PDF、`chroma_db/` 或 `.index_state/`。本地运行需要：

1. 按 `knowledge_config.py` 的 `INDEXED_DOCUMENTS` 放置 7 份 CNOOC PDF；
2. 保留 `data/cnooc/sources.csv`，并确认 PDF 的 SHA-256 与清单一致；
3. 仅在明确需要时运行 `python index_documents.py` 构建/更新索引。

`index_documents.py` 会写 `chroma_db/` 和 `.index_state/`；不要把它当作只读操作。运行后可用 `/api/v1/documents` 验证实际索引。

## 配置

若尚无 `.env`：

```bash
cp .env.example .env
```

然后在 `.env` 填入自己的 `DEEPSEEK_API_KEY`。配置项见 `.env.example`；不要提交 `.env`。缺少 Key 时 `/health` 仍可用；查询若检索到内容并需要调用 LLM，会返回 503 `LLM_NOT_CONFIGURED`。

## 启动 API

```bash
uvicorn app.api:app --host 127.0.0.1 --port 8000
```

浏览器打开 `http://127.0.0.1:8000/`，即可在对话框里连续提问，查看答案、引用文件和页码。网页与 API 使用同一个服务，**只需启动一次**，不用每次运行 `main.py`。页面会显示实际索引状态；若索引或 API Key 未就绪，提问时会显示错误。当前每次问题独立处理，页面里的历史仅在本次打开期间显示，刷新即清空；后端没有多轮记忆。首次问答可能需要加载本地检索模型，速度较慢。

三个端点：

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/v1/documents
curl -X POST http://127.0.0.1:8000/api/v1/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"员工入职时需要签署什么合规文件？","top_k":3}'
```

- `/health` 仅表示进程存活，不加载模型、不要求 API Key、不检查索引。
- `/api/v1/query` 返回 `request_id`、`answer`、结构化 `sources`、`rerank_score`、`retrieval_count`、`timings_ms`。`sources` 由本次检索结果元数据生成（`chunk_id`、路径、页码、`source_url` 等），不会使用白名单或全局列表；与 CLI 一致，只包含答案中 `[资料 N]` 明确引用的来源，未引用则为空。
- `/api/v1/documents` 只读返回当前实际已索引文档；索引缺失/为空返回 503 `INDEX_NOT_READY`。
- 错误响应统一为 `{"code": "...", "message": "...", "request_id": "..."}`，并带 `X-Request-ID` 响应头。

## CLI

```bash
python main.py
```

CLI 仍输出旧字段 `answer`、`sources`（路径 + 页码字符串）、`rerank_score`，默认 Top-3、候选 5；它和 API 使用同一个 `RAGService`。

## 测试

新 mock 服务/API 测试（不调用 DeepSeek、不写 Chroma）：

```bash
python -m unittest discover -s tests -p 'test_app.py' -v
```

旧解析测试：

```bash
python -m unittest discover -s tests -p 'test_ingestion.py' -v
```

旧迁移测试中不打开 Chroma 的部分：

```bash
python -m unittest discover -s tests -p 'test_cnooc_migration.py' \
  -k test_allowlist -k test_chunks -k test_state -k test_missing -v
```

注意：`test_bm25_and_vector_use_identical_ids` 会打开 Chroma `PersistentClient`，在只读验收环境中不要运行；`/api/v1/documents` 已使用只读 SQLite 检查真实索引。

## 已知限制

- 本地单用户原型；无身份认证、ACL、上传、Docker、正式评测。
- 本地对话页面只用于单用户测试；未提供账号、会话持久化或多轮上下文。请仅绑定 `127.0.0.1` 使用，不要直接暴露到公网。
- 检索/重排模型首次查询时懒加载，第一次请求会较慢。
- `/api/v1/query` 的引用只做“编号 → 本次检索来源”的映射；没有 Chunk 级语义支持校验，编号存在不等于答案结论有证据支持。
- 本次实现没有调用真实 DeepSeek API；API 测试全部使用 mock LLM。真实端到端问答需要配置 Key 后自行验证。
- 索引是本地快照；PDF/Chroma/状态文件不在 Git 中，新环境需按上面的数据准备步骤重建。
