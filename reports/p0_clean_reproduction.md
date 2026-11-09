# P0 干净环境复现记录（RAG-20261109-001）

日期：2026-11-09（Australia/Sydney）  
目标：在不写入生产 `chroma_db/`、`.index_state/`、原始 PDF 和 `.env` 的前提下，按 README 验证依赖安装、索引重建、API 启动、评测和测试。

## 环境

- 新 venv：`/tmp/cnooc_clean_venv`，Python 3.12.14。
- 隔离副本：`/tmp/cnooc_clean_repro`，复制当前代码；只放 7 份白名单 PDF 和 `data/cnooc/sources.csv`。
- 依赖安装：`/tmp/cnooc_clean_venv/bin/pip install -r requirements.txt`，成功安装固定版本（包括 `chromadb==1.5.9`、`sentence-transformers==6.1.0`、`torch==2.14.1`、`fastapi==0.138.0`、`uvicorn==0.54.0`）。
- 模型缓存：本机已有 `BAAI/bge-small-zh-v1.5` 和 `BAAI/bge-reranker-base` 缓存；未在干净副本重新下载模型权重。

## 索引重建

命令（在隔离副本目录执行）：

```bash
/tmp/cnooc_clean_venv/bin/python index_documents.py
```

结果：

```text
已索引：data/cnooc/compliance/employee_compliance.pdf，43 chunks
已索引：data/cnooc/compliance/director_ethics_2026.pdf，29 chunks
已索引：data/cnooc/governance/articles_2025.pdf，89 chunks
已索引：data/cnooc/governance/nomination_committee_2025.pdf，4 chunks
已索引：data/cnooc/governance/audit_committee.pdf，18 chunks
已索引：data/cnooc/governance/remuneration_committee.pdf，7 chunks
已索引：data/cnooc/governance/strategy_sustainability_committee.pdf，4 chunks
Collection: cnooc_knowledge; PDF: 7; Chunks: 194
耗时：7.3 秒
```

## API 启动

命令（干净 venv + 隔离副本代码）：

```bash
/tmp/cnooc_clean_venv/bin/uvicorn --app-dir /tmp/cnooc_clean_repro app.api:app \
  --host 127.0.0.1 --port 8011
```

实测：

- `GET /health` → HTTP 200，`{"status":"ok"}`。
- `GET /api/v1/documents` → HTTP 200，Collection `cnooc_knowledge`，7 份文档，194 Chunk。

## 评测复现

命令：

```bash
/tmp/cnooc_clean_venv/bin/python /tmp/cnooc_clean_repro/eval/run_cnooc_eval.py
```

结果与仓库正式报告一致：

| 方法 | Hit@1 | Hit@3 | Hit@10 | Recall@10 | MRR@10 |
|---|---:|---:|---:|---:|---:|
| Dense-only | 61.54% | 84.62% | 100.00% | 99.04% | 0.7548 |
| BM25-only | 50.00% | 50.00% | 73.08% | 67.95% | 0.5472 |
| Hybrid/RRF | 73.08% | 92.31% | 96.15% | 92.31% | 0.8109 |
| Hybrid/RRF+Reranker | 92.31% | 96.15% | 96.15% | 92.31% | 0.9423 |

## 完整测试

命令：

```bash
PYTHONPATH=/tmp/cnooc_clean_repro \
/tmp/cnooc_clean_venv/bin/python -m unittest discover \
  -s /tmp/cnooc_clean_repro/tests -p 'test_*.py' -v
```

结果：`Ran 46 tests ... OK`。

说明：首次只放 7 份白名单 PDF 时，历史测试 `test_real_pdf_page_metadata_and_corpus_isolation` 因期望 `sources.csv` 中 9 份文档而失败，`test_state_is_stable_and_legacy_files_are_outside_data` 因缺少 legacy 状态文件失败；把 2 份非白名单 PDF 和 `.index_state/legacy_document_hashes.json` 复制到隔离副本后，完整套件通过。这两个失败是隔离副本资料不完整，不是产品代码失败，也不是正式索引混入非白名单文档。

## 生产数据保护

- 评测前生产 `chroma_db/` 快照 SHA-256：`c45504a26cec0942637c4a3da6c0544699fea32f048af2f86ec97d525dc9d44f`。
- 评测/测试后重新计算仍为同一值；未写入生产 `chroma_db/`。
- 隔离副本没有复制 `.env`，因此没有在干净副本调用真实 DeepSeek；真实问答证据在现有环境完成并单独记录。

## 未完成项

- 干净副本未重新下载 Hugging Face 模型权重（使用本机缓存）。
- 浏览器内真实提问未在干净副本验证；API 端点已验证。
