# CNOOC 检索对照评测报告

- 数据集：`eval/cnooc_eval_v1.json`
- 数据集版本：`cnooc_eval_v1.0`
- 数据集 SHA-256：`9359469bfae0b6b34188d35713aff2f98c18b95576b417260c0b68d04fd6a384`
- 索引快照 SHA-256：`c45504a26cec0942637c4a3da6c0544699fea32f048af2f86ec97d525dc9d44f`
- Collection：`cnooc_knowledge`；Chunk 数：194
- Embedding：`BAAI/bge-small-zh-v1.5`
- Reranker：`BAAI/bge-reranker-base`
- 候选预算：10；RRF k：60；BM25 分词：jieba
- 有答案题：26；无答案题：5
- 运行命令：`eval/run_cnooc_eval.py`
- 运行时间：2026-11-09T10:05:10.374970+00:00（UTC），耗时 21.9 秒
- 预热：每个方法先用“员工入职时需要签署哪些合规文件？”预热一次；下表耗时为预热后的单次调用平均，不含模型懒加载。预热耗时：{'dense': 4.1, 'bm25': 0.3, 'hybrid_rrf': 0.0, 'hybrid_rrf_reranker': 4.2}
- Python：3.12.14；平台：`macOS-26.6.2-arm64-arm-64bit`
- Git HEAD：`28ffdd6d6f42bfba41b256d3d85d9cee6b166fa2`

## 指标定义

- **Hit@K**：Top-K 候选中至少有一个 Chunk ID 属于该题可接受相关集合的题目比例；分母为全部有答案题。
- **Recall@K**：Top-K 候选中命中的可接受相关 Chunk 数 / 该题可接受相关 Chunk 总数；再对有答案题取平均。多证据题按相关集合计算。
- **MRR@10**：首个相关 Chunk 排名倒数的平均值；未命中记 0；分母为全部有答案题。
- 所有方法使用相同题目、相同索引快照和 10 个候选预算。实际返回数少于 10 的题目已在逐题记录中标记；本报告不虚构未返回的候选。
- 无答案题不进入上述检索指标分母；本任务没有对全部题目运行 LLM，因此不报告答案准确率或拒答率。

## 汇总（有答案题，分母 = 26）

| 方法 | Hit@1 | Hit@3 | Hit@5 | Hit@10 | Recall@5 | Recall@10 | MRR@10 | 平均耗时 ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| dense | 61.54% | 84.62% | 92.31% | 100.00% | 88.46% | 99.04% | 0.7548 | 5.3 |
| bm25 | 50.00% | 50.00% | 65.38% | 73.08% | 57.05% | 67.95% | 0.5472 | 0.2 |
| hybrid_rrf | 73.08% | 92.31% | 96.15% | 96.15% | 91.03% | 92.31% | 0.8109 | 5.4 |
| hybrid_rrf_reranker | 92.31% | 96.15% | 96.15% | 96.15% | 92.31% | 92.31% | 0.9423 | 323.9 |

## 无答案题

- 共 5 道；未做 LLM 全量评测，因此不计算拒答准确率。
- 逐题候选仍保存在 JSON 中，供后续人工检查；无答案题不混入有答案检索指标。

## 失败案例（有答案题）

| 方法 | 题目 | 类别 | 首个相关排名 | 失败原因 | 缺失 Chunk |
|---|---|---|---:|---|---|
| dense | X03 审核、提名、薪酬、战略与可持续发展四个委员会的章程分别由董事会何时批准和采用？ | cross_document | 2 | partial_expected_chunks_missing | data/cnooc/governance/remuneration_committee.pdf::p0004::c0001 |
| bm25 | E03 员工离职后在竞业和保密方面仍有哪些义务？ | multi_evidence | 1 | partial_expected_chunks_missing | data/cnooc/compliance/employee_compliance.pdf::p0007::c0002 |
| bm25 | A01 组织章程细则中公司的正式名称是什么？ | synonym | 未命中 | no_expected_chunk_in_top_10 | data/cnooc/governance/articles_2025.pdf::p0006::c0001 |
| bm25 | A03 公司召开股东周年大会和其他股东大会，分别需要提前多少天发出书面通知？ | numeric_date | 未命中 | no_expected_chunk_in_top_10 | data/cnooc/governance/articles_2025.pdf::p0016::c0001 |
| bm25 | A04 董事会会议的法定人数和表决规则是什么？ | numeric_date | 未命中 | no_expected_chunk_in_top_10 | data/cnooc/governance/articles_2025.pdf::p0028::c0001, data/cnooc/governance/articles_2025.pdf::p0028::c0002 |
| bm25 | AU03 审核委员会如何接收和处理员工关于财务报告、内部监控或审计事务的投诉？ | clause | 未命中 | no_expected_chunk_in_top_10 | data/cnooc/governance/audit_committee.pdf::p0006::c0001 |
| bm25 | S01 战略与可持续发展委员会的宗旨是什么？ | clause | 未命中 | no_expected_chunk_in_top_10 | data/cnooc/governance/strategy_sustainability_committee.pdf::p0001::c0001 |
| bm25 | S02 战略与可持续发展委员会的组成和会议法定人数有什么要求？ | numeric_date | 未命中 | no_expected_chunk_in_top_10 | data/cnooc/governance/strategy_sustainability_committee.pdf::p0001::c0001 |
| bm25 | X01 员工和董事/高级管理人员发现利益冲突时，分别应向谁报告？ | cross_document | 1 | partial_expected_chunks_missing | data/cnooc/compliance/employee_compliance.pdf::p0007::c0002 |
| bm25 | X02 审核委员会和薪酬委员会在会议文件发送时间上有什么共同要求？ | cross_document | 5 | partial_expected_chunks_missing | data/cnooc/governance/audit_committee.pdf::p0002::c0001 |
| bm25 | X03 审核、提名、薪酬、战略与可持续发展四个委员会的章程分别由董事会何时批准和采用？ | cross_document | 未命中 | no_expected_chunk_in_top_10 | data/cnooc/governance/audit_committee.pdf::p0010::c0001, data/cnooc/governance/nomination_committee_2025.pdf::p0003::c0001, data/cnooc/governance/remuneration_committee.pdf::p0004::c0001, data/cnooc/governance/strategy_sustainability_committee.pdf::p0003::c0001 |
| hybrid_rrf | A01 组织章程细则中公司的正式名称是什么？ | synonym | 未命中 | no_expected_chunk_in_top_10 | data/cnooc/governance/articles_2025.pdf::p0006::c0001 |
| hybrid_rrf | A04 董事会会议的法定人数和表决规则是什么？ | numeric_date | 1 | partial_expected_chunks_missing | data/cnooc/governance/articles_2025.pdf::p0028::c0001 |
| hybrid_rrf | X03 审核、提名、薪酬、战略与可持续发展四个委员会的章程分别由董事会何时批准和采用？ | cross_document | 3 | partial_expected_chunks_missing | data/cnooc/governance/audit_committee.pdf::p0010::c0001, data/cnooc/governance/remuneration_committee.pdf::p0004::c0001 |
| hybrid_rrf_reranker | A01 组织章程细则中公司的正式名称是什么？ | synonym | 未命中 | no_expected_chunk_in_top_10 | data/cnooc/governance/articles_2025.pdf::p0006::c0001 |
| hybrid_rrf_reranker | A04 董事会会议的法定人数和表决规则是什么？ | numeric_date | 2 | partial_expected_chunks_missing | data/cnooc/governance/articles_2025.pdf::p0028::c0001 |
| hybrid_rrf_reranker | X03 审核、提名、薪酬、战略与可持续发展四个委员会的章程分别由董事会何时批准和采用？ | cross_document | 1 | partial_expected_chunks_missing | data/cnooc/governance/audit_committee.pdf::p0010::c0001, data/cnooc/governance/remuneration_committee.pdf::p0004::c0001 |

## 逐题候选

逐题、逐方法的候选 Chunk ID、来源、页码、名次、分数与命中状态保存在同目录 JSON 的 `methods[].records[]` 中。

