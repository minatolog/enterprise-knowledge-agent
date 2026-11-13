# 企业扩展运行与验收

本扩展属于 RAG-20261113-002，独立于原 `app.api`。新增 API 为 `/api/v2/*`，文件、SQL、Chroma 和开发凭据均放在 Git 忽略的 `.enterprise/`。旧 CNOOC 索引、原始 PDF、来源清单和评测数据不修改。

## 本地启动

```bash
conda activate agent
python -m pip install -r requirements-enterprise.txt
python scripts/setup_enterprise.py
python scripts/enterprise.py token --tenant demo --groups staff --roles admin
python scripts/enterprise_import.py
python scripts/enterprise.py serve
```

接口文档：`http://127.0.0.1:8030/docs`。本地模式用 SQLite、文件对象存储、有界内存缓存和同步任务；开启真实 PostgreSQL/Redis/RabbitMQ 使用下文基础设施模式，不能把两个后端的验收混为一谈。

`setup_enterprise.py` 生成随机开发凭据，权限为 0600；不打印密码或 Token。开发 Token 保存在 `.enterprise/operator.token`，一小时过期；监控 Token 24 小时过期，重新执行 setup 刷新。生成的凭据不是企业 SSO；不要将开发模式暴露到公网。

API 调用示例（Token 只读私有文件，不在终端打印）：

```python
from pathlib import Path
import httpx

headers = {"Authorization": "Bearer " + Path(".enterprise/operator.token").read_text().strip()}
response = httpx.post("http://127.0.0.1:8030/api/v2/query",
    headers=headers, json={"question": "员工出差需要遵守什么规定？", "session_id": "demo-session"}, timeout=120)
print(response.status_code)
```

有证据时默认先生成、再进行一次独立的 LLM 证据核验；因此可能产生两次模型调用。遵守原 DEEPSEEK 环境配置，无 Key 时返回明确错误。没有证据则跳过生成。`ENTERPRISE_VERIFY_ANSWERS=false` 仅可用于明确标记的结构/集成测试；它只做引用结构检查，不能宣称完成语义核验。

## 接口

| 接口 | 行为 |
|---|---|
| `GET /health` | 不含敏感状态的存活检查 |
| `GET /ready`、`GET /metrics` | 管理员后端检查、Prometheus 指标 |
| `POST /api/v2/documents` | multipart 上传，title、groups JSON 数组、可选 document_id、file |
| `GET /api/v2/documents` | 仅返回当前租户且有权限的资料 |
| `PUT /api/v2/documents/{id}/acl` | 管理员调整可访问用户组，立即影响检索、缓存、历史和原文 |
| `DELETE /api/v2/documents/{id}` | 撤回文档，保留可追溯版本，立即从授权集合中排除 |
| `GET /api/v2/documents/{id}/original?release_id=...` | 再鉴权后返回引用所对应版本的原件 |
| `POST /api/v2/index/publish` | 创建入库任务，返回 job_id；不是立即宣布入库成功 |
| `GET /api/v2/jobs/{id}` | queued/running/succeeded/failed 与有限错误类型 |
| `POST /api/v2/jobs/{id}/retry` | 手动重试失败任务，总次数受限 |
| `GET /api/v2/index/releases` | 当前版本及历史发布列表 |
| `POST /api/v2/index/rollback/{id}` | 切换租户的已存在快照，不恢复撤销权限 |
| `POST /api/v2/connectors/sync` | allowlist HTTPS 的 OA JSON/Confluence 页面同步 |
| `POST /api/v2/query` | 授权检索 → LangChain/LangGraph → 有预算上下文 → 生成 → 核验 |
| `GET /api/v2/sessions/{id}` | 只返回当前用户、租户、权限和索引版本一致的历史 |

## PostgreSQL、S3、Redis、RabbitMQ 与观测服务

```bash
python scripts/setup_enterprise.py
python scripts/start_enterprise_infra.py
python scripts/enterprise.py bucket --env .enterprise/runtime.env
python scripts/enterprise.py worker --env .enterprise/runtime.env
# 另开终端启动 API
python scripts/enterprise.py serve --env .enterprise/runtime.env
```

`compose.enterprise.yml` 使用 PostgreSQL、Redis、RabbitMQ、SeaweedFS S3、OTel Collector、Prometheus 和 Grafana。初始化脚本用 named volumes 和 `docker cp` 注入配置，避免依赖宿主目录共享；不要跳过配置注入步骤直接启动空卷。S3 bucket 需通过 bucket 命令创建。

镜像应用 profile：`docker compose --env-file .enterprise/compose.env -f compose.enterprise.yml --profile app up -d --build`。容器内模型缓存独立，首次需要下载模型。应用与 worker 的共享 `/state` 使用同一 named volume；单机文件锁不是跨主机分布式锁。

Dockerfile 以非 root 用户运行；`.dockerignore` 排除 `.env`、PDF、数据库、报告和开发状态。CI 文件只提供可执行流程，本次未推送或运行 GitHub Actions。完整镜像构建和部署需以实际记录为准。

当前机器的 S3/OTel/Prometheus/Grafana 容器启动及完整应用镜像尚未验收；见任务 ISSUE-01。已经实测的 PostgreSQL/Redis/RabbitMQ 联调使用本地模型和模拟生成，没有真实模型费用。

## OIDC 与企业数据源

企业部署设置 `ENTERPRISE_AUTH_MODE=oidc`、`ENTERPRISE_ISSUER`、`ENTERPRISE_AUDIENCE`、`ENTERPRISE_JWKS_URL`。仅接受 RS256，验证签名、issuer、audience、exp、iat、sub 和 tenant_id；groups/roles 只能来自已验签声明。IdP 必须配置这些映射；前端登录和授权码流程由企业 SSO 接入侧负责。

连接器配置 `ENTERPRISE_CONNECTOR_HOSTS=wiki.example.com,oa.example.com` 和可选 `ENTERPRISE_CONNECTOR_TOKEN`。只接受明确 allowlist 的 HTTPS host，不跟随重定向，限制响应体。支持 `{"documents":[{"id":"...","title":"...","text":"..."}]}` 和 Confluence `results[].body.storage.value`。分页 URL 需分别明确配置，不会无限遍历整个站点；当前没有所有厂商 OA 的专属协议或远端删除事件自动识别。

定时同步：将配置 JSON 放在安全位置，设置 `ENTERPRISE_CONNECTORS_FILE`，格式为列表，每项有 url、tenant_id、groups。运行 `celery -A app.enterprise.worker:app beat --schedule=.enterprise/celerybeat`，与同环境 worker 配套；默认间隔 300 秒。容器 profile 含 scheduler，文件必须存在于对应容器可读的安全路径。没有真实企业平台账号，所以远端身份和数据同步仍需现场联调。

## OCR 与表格

```bash
python -m pip install -r requirements-ocr.txt
```

设置 `ENTERPRISE_PARSER=docling` 后重新启动对应入库 worker，启用 PDF OCR 和表格结构识别，保留 provenance 页码。首次下载解析模型，资源消耗高于 basic。已经用新建单页扫描表格测试提取城市与金额；不代表所有版式和扫描质量都已验证。基础 Dockerfile 默认 basic；需要 OCR 时用安装 requirements-ocr 的派生镜像或本地环境。

## 备份、恢复、评测和压测

备份前停止写入/任务，保留导出文件在安全位置（包含文档和历史，不能提交 Git）。

```bash
python scripts/enterprise_backup.py backup .enterprise/backups/manual --env .enterprise/local.env
python scripts/enterprise_backup.py restore .enterprise/backups/manual .enterprise/restored --env .enterprise/local.env
# PostgreSQL 可恢复到一个全新的 restore_* 数据库，拒绝覆盖同名库
python scripts/enterprise_backup.py restore .enterprise/backups/manual .enterprise/restored-pg --env .enterprise/runtime.env --postgres-database restore_check
python scripts/enterprise_loadtest.py --requests 20 --workers 4
python scripts/enterprise_eval.py .enterprise/reviewed-answers.json --output .enterprise/eval.json
```

备份导出全部元数据和对象、Chroma 快照并保存 SHA-256；恢复验证校验值且只允许新目录。跨后端恢复对象先落到恢复目录，本地对象后端可直接使用；恢复进 S3 服务还需把对象导入目标新 bucket 并核对清单，不能只恢复 SQL。

压测默认仅健康接口；带 `--query` 和 `--token-file` 才进行有模型费用的问答请求。已测的健康接口并发不证明真实 RAG P95 或生产容量。

生成评测输入是 JSON 列表，每项包含 id、question、answer、实际 evidence（含 text），可选 human_correct（人工布尔标注）和 requires_abstention。`--llm-judge --max-calls 3` 显式启用限额核验；没有人审标签则 human_accuracy 为 null，不伪造答案准确率。完整业务生成集、对抗样本及生产 SLA 尚需真实验收。

证据与更新架构见 [本次交付报告](../reports/RAG-20261113-002_delivery.md)。
