# RAG-20261109-001 — Codex 独立验收

- 日期：2026-11-09（Australia/Sydney）
- 工具/模型：Codex / gpt-6.1-sol
- 基线：main @ 28ffdd6d6f42bfba41b256d3d85d9cee6b166fa2，审查 DeepSeek 留下的未提交修改。
- 指令：[本轮验收请求](../docs/ai_workflow/prompts/debugging/RAG-20261109-001_acceptance_review.md)；[原 P0 任务](../docs/ai_workflow/prompts/implementation/RAG-20261109-001_p0_completion.md)。
- 结论：本任务约定的 P0 本地交付验收通过。测试、检索结果与来源记录有可核验的实物证据，没有发现阻止当前本地版本交付的问题；下列验收边界仍应保留。

## 独立验证

| 项目 | 本轮检查与结果 |
|---|---|
| 代码修改 | 业务代码仅 llm.py 删除两条角色扮演/安慰指令；未改检索排序。新增评测脚本、数据集、测试、报告和 README。 |
| 应用测试 | 主环境复跑 test_app.py：32 项通过。 |
| 新评测测试 | 主环境复跑 test_cnooc_eval.py：5 项通过；逐题证据短句能在声明的 PDF 页和 Chunk 中找到，索引检查在只读 SQLite/临时副本上完成。 |
| 完整测试 | 复用 DeepSeek 创建的 /tmp/cnooc_clean_venv 和 /tmp/cnooc_clean_repro，核对服务、前端、生成、评测、测试与依赖文件内容和当前仓库一致后，复跑完整套件：46 项通过。此项不等于本轮重新安装了依赖。 |
| 四路检索复现 | 在本地缓存模型、HF 离线模式和临时 Chroma 副本上复跑；四种方法的 31 题 Top-10 Chunk ID 排列均与 DeepSeek 原 JSON 完全一致。另从候选列表独立重算 Hit@1、Hit@3 和 MRR，与报告一致。 |
| 默认网页检索 | 另测 top_k=3、candidate_k=5：Hit@1 24/26，Hit@3 25/26；全部标签证据进入 Top-3 为 22/26。逐题结果见下方链接。 |
| 真实问答记录 | 检查 /tmp/p0_q1.json 至 p0_q4.json 的实际响应文件，request_id、答案短片段与来源顺序能对应现有问答核验报告。另抽查员工手册、组织章程、提名/战略委员会原页文本；本轮没有再次调用 DeepSeek，原任务 4 次额度已用尽。 |
| 原资料与索引保护 | 9 份 PDF 的 SHA-256 均与 sources.csv 一致。生产 Chroma 目录哈希在本轮前后均为 c45504a26cec0942637c4a3da6c0544699fea32f048af2f86ec97d525dc9d44f，亦与 DeepSeek 记录一致。 |
| Git 与敏感内容 | git diff --check 通过；对待提交文本做凭据模式检查未命中。没有执行 Commit、Tag 或 Push。 |

本轮实际命令（环境变量略）：

```bash
/opt/anaconda3/envs/agent/bin/python -m unittest discover -s tests -p test_app.py -q
/opt/anaconda3/envs/agent/bin/python -m unittest discover -s tests -p test_cnooc_eval.py -q
/opt/anaconda3/envs/agent/bin/python eval/run_cnooc_eval.py --output-dir /tmp/cnooc_codex_acceptance_eval
PYTHONPATH=/tmp/cnooc_clean_repro /tmp/cnooc_clean_venv/bin/python -m unittest discover -s /tmp/cnooc_clean_repro/tests -p 'test_*.py' -q
git diff --check
```

## 指标解释与限制

- 31 题含 26 道有答案题和 5 道无答案题；题目为 AI 草拟、来源文本已核对，尚未经过用户逐题人工审阅。
- Reranker 的 Hit@1=92.31% 是 24/26 题第一条结果落在标签相关集合内；不是答案正确率，也不是所有证据完整率。
- 原评测配置用 10 个 Reranker 候选，网页默认只重排 5 个候选并输出 3 条。本轮补测前两项命中率相同，只能说明当前数据集上的结果，不能推断任意问题均等价。
- 默认 Top-3 未找齐标签证据的题目为 E03、A01、A04、X03；其中跨文档 X03 要求 4 个 Chunk，Top-3 本身不能同时容纳全部 4 条证据。没有据此修改标准标签或调生产参数。
- 真实问答的独立重放、浏览器内完整提问和移动端体验未在本轮验证。现有 4 次真实调用记录只能证明有限样例，不能估计整体答案准确率、拒答率或引用语义支持率。
- 原文抽查使用 pypdf 提取完整相关页文本；本机缺少 PDF 渲染工具，本轮没有验证视觉阅读顺序。
- 新建 venv 安装依赖、重建隔离索引的历史执行由 DeepSeek 报告记录；本轮确认环境/副本存在、核心文件内容一致、完整测试和检索结果可复现，但没有重新安装环境或重算文档 Embedding。

## 本轮文档修正

- 修正 README 架构图中的 BM25 数据来源：实际从 Chroma 读取 Chunk，在首次检索时懒加载；不是离线 Chunking 后直接建立另一个持久索引。
- 补充候选 10 的评测与网页默认候选 5 的区分及补测结果。
- 更新任务当前状态，保留 DeepSeek 执行记录和原始评测结果。

相关证据：[默认配置逐题结果](eval/cnooc_default_acceptance_20261109.json)、[四路原报告](eval/cnooc_retrieval_eval_v1.md)、[真实问答记录](p0_real_qa_verification.md)、[干净环境记录](p0_clean_reproduction.md)。

## 验收后用户风格更正：2026-11-09

用户明确要求恢复可爱口吻，llm.py 已逐字恢复原有角色/安慰指令，现与 HEAD 一致；上文“删除角色指令”和 Q4 正式语气描述的是验收当时的临时版本。恢复后应用测试 32 项通过，事实和引用约束保留；没有追加真实 DeepSeek 调用。
