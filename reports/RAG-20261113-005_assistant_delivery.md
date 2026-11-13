# CNOOC Enterprise Knowledge Assistant · 前端交付

日期：2026-11-13。任务：RAG-20261113-005。状态：REVIEW（实现与下列检查完成，待用户视觉验收）；未 Commit/Tag/Push。

## 本次实现

| 用户要求 | 实际行为 |
|---|---|
| Grok-inspired专业聊天界面 | 炭黑底、低对比表面、少量蓝色、克制淡入；去除上一版多色光晕/玻璃装饰 |
| 折叠侧栏与历史 | 新对话、搜索、实际日期分组、设置/知识库入口；小屏抽屉 |
| 真实聊天 | 原v1 POST问答、loading/error、Enter/Shift+Enter/输入法组合保护、自动滚动 |
| Markdown与操作 | react-markdown + remark-gfm，列表/代码/表格；复制回答；重新POST同一问题生成并替换该轮 |
| 真实来源 | 引用chip展开文件/页码/路径/Chunk ID/label与官方URL；来源弹层焦点管理/背景inert/Escape退出 |
| 技术透明 | 默认收起的真实候选数、request_id、阶段耗时、返回的重排评分；不将原始分数叫置信度 |
| 知识库 | 真实文档/Chunk数、列表/名称或路径搜索/单文档元数据；只读 |
| 工作流/运行记录 | 原固定图继续可用并懒加载；当前打开期间的实际请求记录 |
| 设置 | Top K、动效偏好、明确的浏览器历史保存开关 |
| 历史保存 | 默认仅内存；主动开启才写入此浏览器真实记录。字段验证、版本、50对话/100轮限制；关闭删本功能存储 |

没有接入当前v1未提供的上传或破坏性操作。没有服务器历史列表，浏览器历史不是后端会话；每次提问独立检索。独立企业v2鉴权/上传不在此次集成范围内，不绕过其认证。

## 数据契约缺口

- `SourceItem` 未返回检索正文/snippet、引用号citation_number；界面显示缺失，不编造证据文本，不自行给来源重新编号冒充正文引用号。
- QueryResponse未返回BM25/Dense分路结果、RRF排名、完整重排候选列表；界面明确列出未暴露字段，不能把架构图当运行日志。
- DocumentsResponse未返回原件总页数、文档分类、更新时间；显示“接口未提供”。现有页码范围不作为PDF总页数统计。
- 原始Prompt附件在验收第4条中途截断，记录仅限实际附件全文。没有伪造后续验收文字。

## 代码与依赖

入口 main.tsx → App.tsx；hooks/useAssistant.ts负责API/对话状态，state/conversations.ts负责保存格式/校验/日期分组，api.ts负责请求契约；components分担Sidebar、Chat、MessageComposer、SourceDetails、Knowledge/Settings/Runs/Workflow页面。

新assistant.css取代旧样式导入；旧样式文件保留，不再堆叠覆盖。现有React/TS/Vite/ReactFlow/lucide复用；仅新增Markdown所需react-markdown/remark-gfm，package-lock固定解析结果。原始HTML和图片渲染关闭，外链仅允许http(s)。不声称已做完整安全审计。

临时使用Prettier 3.6.2格式化本次改动，未添加到运行或开发依赖。发现根.gitignore的lib/规则会漏掉新历史模块，已改放state/，确认git可见，未改用户.gitignore。

## 验证证据

- `npm test --prefix frontend`：6项通过，覆盖持久化回读、空聊天排除、损坏/超大/未知版本记录、错误评分类型、身份去重/轮数上限、链接协议与日期分组。
- agent环境 `python -m unittest discover -s tests -p test_studio.py`：2项通过。
- agent环境 `python -m unittest discover -s tests -p test_app.py`：32项通过。合计40项相关测试；不是完整企业版回归。
- `npm run build --prefix frontend`：TS严格检查与正式构建通过。主JS433.17kB/gzip135.97kB，Flow懒加载190.80kB/gzip63.12kB；主CSS33.21kB/gzip7.66kB，Flow CSS15.87kB/gzip2.67kB。已消除首轮单chunk大于500kB提示；ReactFlow纯客户端构建忽略use client的既有提示仍有。
- 本地 `/studio/` HTTP200；API文档清单实时7文档194Chunk。
- 真实问题：“审计委员会的主要职责是什么？请用 Markdown 分点说明并引用来源。”首次请求 `d3a1152d50da42eda0a75407004ebb2a`，total10634.7ms；重新生成 `ea8a6909335b476391f2a47638f59426`，total12502.0ms。两次真实模型调用成功，不是模拟生成。
- 回答渲染7个列表项；2条引用为audit_committee.pdf第3/9页；技术面板返回候选3、顶层rerank0.0578、引用分数0.0331/0.0578；复制状态为“已复制”；重新生成后仍1轮消息。
- 只读pypdf确认第3页653字符、第9页907字符，均含委员会/审计相关术语。此为页码与资料存在性核对，不是完整答案逐句证据评测。
- 浏览器开启保存→真实问答→刷新恢复1轮/2来源→搜索有/无匹配→关闭保存→刷新空历史；最终恢复默认不保存。未在开发记录保存浏览器完整回答历史或密钥。
- 默认与1440×900桌面、390×844手机视口验证；手机实际innerWidth=scrollWidth=390px，输入框top≈351/bottom≈471px，小于844px视口；抽屉打开后背景inert，来源弹层关闭焦点可恢复。没有覆盖全部设备/浏览器或虚拟键盘组合。
- Flow懒加载后6节点可用；浏览器console error/warn为空。
- `git diff --check`通过。后端/索引/原PDF/评测数据/Python依赖未改，未执行全套生成评测或生产部署。

## 截图

[首页](assistant-ui/welcome.png) · [真实回答](assistant-ui/answer.png) · [来源](assistant-ui/source-details.png) · [手机](assistant-ui/mobile.png)

## 参考与限制

[用户指定参考仓库](https://github.com/bhaktofmahakal/UI-Engineering)仅提供README/提示模板；Demo浏览器返回503 DEPLOYMENT_PAUSED，无法像素核对。此次按照用户明确设计规范原创实现，没有复制限制商业使用的源码或品牌。

既有llm.py包含“鲸鱼娘”角色口吻，真实回答仍受其影响；本轮要求不改后端，因此未修改或在前端篡改回答。其他未实现数据字段、服务器持久会话与鉴权集成见上。当前是可演示本地原型，不是生产验收通过。

[执行记录](../docs/ai_workflow/execution_logs/RAG-20261113-005.md) · [决策](../docs/ai_workflow/decisions/RAG-20261113-005-DECISION-01.md) · [问题记录](../docs/ai_workflow/issues/RAG-20261113-005-ISSUE-01.md)
