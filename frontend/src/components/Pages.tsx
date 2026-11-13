import { lazy, Suspense, useState } from "react";
import {
  Activity,
  BookOpen,
  ChevronRight,
  ExternalLink,
  FileText,
  LoaderCircle,
  RefreshCw,
  Search,
  ShieldCheck,
} from "lucide-react";
import {
  safeLink,
  type DocumentInfo,
  type DocumentList,
  type Source,
} from "../api";
import type { Turn } from "../state/conversations";
import { RunDetails } from "./SourceDetails";
import { steps } from "../flowSteps";
const Flow = lazy(() => import("../flow"));
import MessageComposer from "./MessageComposer";
import { AnswerMarkdown } from "./Chat";
export function KnowledgeBasePage({
  data,
  loading,
  error,
  onRefresh,
}: {
  data: DocumentList | null;
  loading: boolean;
  error: string;
  onRefresh: () => void;
}) {
  const [search, setSearch] = useState(""),
    [selected, setSelected] = useState<DocumentInfo | null>(null);
  const list =
    data?.documents.filter((d) =>
      `${d.source} ${d.relative_path}`
        .toLowerCase()
        .includes(search.toLowerCase()),
    ) || [];
  return (
    <section className="secondary-page">
      <div className="page-intro">
        <div>
          <div className="section-eyebrow">KNOWLEDGE BASE</div>
          <h1>有来源的知识。</h1>
          <p>当前已索引的 CNOOC 官方资料。只读查看，不修改原件。</p>
        </div>
        <button className="button" onClick={onRefresh} disabled={loading}>
          <RefreshCw size={14} className={loading ? "spin" : ""} />
          刷新
        </button>
      </div>
      <div className="knowledge-summary">
        <div>
          <span>索引文档</span>
          <strong>
            {data?.indexed_document_count ?? "—"}
            <small>份</small>
          </strong>
        </div>
        <div>
          <span>知识片段</span>
          <strong>
            {data?.indexed_chunk_count ?? "—"}
            <small>个</small>
          </strong>
        </div>
        <div>
          <span>原件总页数</span>
          <strong className="unknown-metric">接口未提供</strong>
        </div>
        <div>
          <span>Collection</span>
          <code>{data?.collection ?? "—"}</code>
        </div>
      </div>
      <div className="knowledge-toolbar">
        <h2>文档清单</h2>
        <label className="document-search">
          <Search size={15} />
          <input
            aria-label="搜索文档"
            placeholder="搜索名称或路径…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
      </div>
      {error && (
        <div className="request-error" role="alert">
          {error}
          <button onClick={onRefresh}>重新读取</button>
        </div>
      )}
      {loading ? (
        <div className="empty-content">
          <LoaderCircle className="spin" size={22} />
          正在读取索引清单
        </div>
      ) : (
        <div className="knowledge-document-list">
          {list.map((doc) => (
            <button
              key={doc.relative_path}
              className={`knowledge-document ${selected?.relative_path === doc.relative_path ? "selected" : ""}`}
              onClick={() => setSelected(doc)}
            >
              <span className="pdf-symbol">
                <FileText size={20} />
              </span>
              <div>
                <strong>{doc.source}</strong>
                <small>
                  {doc.chunk_count} 个片段 · 索引 PDF 页码 {doc.page_start}–
                  {doc.page_end}
                </small>
              </div>
              <span className="indexed-tag">已在索引</span>
              <ChevronRight size={15} />
            </button>
          ))}
          {!error && !list.length && (
            <div className="empty-content">
              {search ? "没有匹配的文档" : "暂无可展示的已索引文档"}
            </div>
          )}
        </div>
      )}
      {selected && (
        <section className="document-inspection">
          <div className="section-eyebrow">DOCUMENT METADATA</div>
          <h2>{selected.source}</h2>
          <dl>
            <dt>来源路径</dt>
            <dd>
              <code>{selected.relative_path}</code>
            </dd>
            <dt>索引 PDF 页码范围</dt>
            <dd>
              {selected.page_start}–{selected.page_end}（不是原件总页数统计）
            </dd>
            <dt>知识库标识</dt>
            <dd>{selected.knowledge_base || "未提供"}</dd>
            <dt>文档分类 / 更新时间</dt>
            <dd>当前 v1 接口未提供</dd>
          </dl>
          {safeLink(selected.source_url) && (
            <a
              className="button"
              href={safeLink(selected.source_url)}
              target="_blank"
              rel="noreferrer"
            >
              打开官方原文
              <ExternalLink size={14} />
            </a>
          )}
        </section>
      )}
      <p className="page-note">
        <ShieldCheck size={13} />
        索引清单不代表后台正在同步；当前页面未接入上传、删除和入库任务。
      </p>
    </section>
  );
}
export function SettingsPage({
  topK,
  onTopK,
  save,
  onSave,
  storageError,
  motion,
  onMotion,
  reduced,
}: {
  topK: number;
  onTopK: (n: number) => void;
  save: boolean;
  onSave: (value: boolean) => void;
  storageError: string;
  motion: boolean;
  onMotion: (value: boolean) => void;
  reduced: boolean;
}) {
  return (
    <section className="secondary-page settings-page">
      <div className="page-intro">
        <div>
          <div className="section-eyebrow">PREFERENCES</div>
          <h1>让它更适合你。</h1>
          <p>仅影响本地界面与下一次问答，不更改后端检索架构。</p>
        </div>
      </div>
      <div className="settings-group">
        <h2>问答</h2>
        <label className="setting-row">
          <span>
            <strong>返回片段数量</strong>
            <small>发送给现有问答接口的 top_k 参数。</small>
          </span>
          <select
            aria-label="默认返回片段数量"
            value={topK}
            onChange={(e) => onTopK(Number(e.target.value))}
          >
            <option value={3}>Top 3</option>
            <option value={5}>Top 5</option>
            <option value={8}>Top 8</option>
          </select>
        </label>
        <div className="setting-information">
          <BookOpen size={16} />
          <p>
            每次请求独立检索。聊天分组仅组织界面记录，不会自动把历史传入模型。
          </p>
        </div>
      </div>
      <div className="settings-group">
        <h2>历史与隐私</h2>
        <label className="setting-row">
          <span>
            <strong>将对话保存在此浏览器</strong>
            <small>
              开启后会保存问题、回答与引用元数据。不会上传到新的服务；同一浏览器同源页面可读取。
            </small>
          </span>
          <input
            type="checkbox"
            role="switch"
            aria-label="将对话保存在此浏览器"
            checked={save}
            onChange={(e) => onSave(e.target.checked)}
          />
        </label>
        <p className="setting-caption">
          {save
            ? "已开启浏览器保存。最多保存最近 50 个对话，每个最近 100 轮；刷新可恢复。"
            : "默认关闭。当前对话只保存在页面内存中，刷新后清空。"}{" "}
          关闭此选项会删除此功能的本地历史副本，当前页面记录仍保留。
        </p>
        {storageError && (
          <div className="request-error" role="alert">
            {storageError}
          </div>
        )}
      </div>
      <div className="settings-group">
        <h2>外观与交互</h2>
        <label className="setting-row">
          <span>
            <strong>克制的界面动效</strong>
            <small>
              {reduced
                ? "系统已启用减少动态效果，当前保持静态。"
                : "页面淡入、状态过渡与工作流装饰连线。"}
            </small>
          </span>
          <input
            type="checkbox"
            role="switch"
            aria-label="界面动效"
            checked={motion}
            onChange={(e) => onMotion(e.target.checked)}
          />
        </label>
      </div>
      <div className="settings-group">
        <h2>当前连接</h2>
        <dl>
          <dt>问答接口</dt>
          <dd>
            <code>POST /api/v1/query</code>
          </dd>
          <dt>文档清单</dt>
          <dd>
            <code>GET /api/v1/documents</code>
          </dd>
          <dt>后端会话与文件上传</dt>
          <dd>当前 v1 未接入；独立 v2 企业入口需要单独鉴权。</dd>
        </dl>
      </div>
    </section>
  );
}
export function RunsPage({
  runs,
  onSource,
}: {
  runs: Turn[];
  onSource: (s: Source) => void;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <section className="secondary-page">
      <div className="page-intro">
        <div>
          <div className="section-eyebrow">REQUEST ACTIVITY</div>
          <h1>每一次请求，都可回看。</h1>
          <p>仅记录本次打开期间的请求；不是服务器审计日志。</p>
        </div>
      </div>
      {!runs.length ? (
        <div className="empty-content spacious">
          <Activity size={28} />
          <h2>还没有请求记录</h2>
          <p>发起问答后，在这里检查真实来源与阶段耗时。</p>
        </div>
      ) : (
        <div className="request-list">
          {runs.map((turn) => (
            <section className="request-item" key={turn.id}>
              <button
                className="request-item-header"
                onClick={() =>
                  setSelected(selected === turn.id ? null : turn.id)
                }
              >
                <span
                  className={`request-dot ${turn.result ? "success" : "error"}`}
                />
                <div>
                  <strong>{turn.question}</strong>
                  <small>
                    {turn.result?.request_id || "未返回 request_id"}
                  </small>
                </div>
                <time>
                  {new Date(turn.createdAt).toLocaleTimeString("zh-CN", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </time>
                <ChevronRight size={15} />
              </button>
              {selected === turn.id && (
                <div className="request-body">
                  <RunDetails turn={turn} onSource={onSource} />
                </div>
              )}
            </section>
          ))}
        </div>
      )}
    </section>
  );
}
export function WorkflowPage({
  animated,
  pending,
  draft,
  onDraft,
  onSend,
  topK,
  onTopK,
  onNotice,
  last,
}: {
  animated: boolean;
  pending: boolean;
  draft: string;
  onDraft: (value: string) => void;
  onSend: () => void;
  topK: number;
  onTopK: (n: number) => void;
  onNotice: (s: string) => void;
  last?: Turn;
}) {
  const [selected, setSelected] = useState("retrieve"),
    step = steps.find((s) => s.id === selected)!;
  return (
    <section className="assistant-workflow">
      <div className="workflow-canvas">
        <Suspense
          fallback={<div className="empty-content">正在加载工作流画布…</div>}
        >
          <Flow
            animated={animated}
            running={pending}
            onSelect={setSelected}
            onNotice={onNotice}
          />
        </Suspense>
      </div>
      <aside className="workflow-inspector">
        <div className="section-eyebrow">FIXED RAG PIPELINE</div>
        <h2>
          <step.icon size={19} />
          {step.title}
        </h2>
        <p>{step.description}</p>
        <code className="backend-node">{step.id}</code>
        <h3>测试问答</h3>
        <MessageComposer
          value={draft}
          onChange={onDraft}
          onSend={onSend}
          pending={pending}
          topK={topK}
          onTopK={onTopK}
          compact
        />
        {last?.error && <div className="request-error">{last.error}</div>}
        {last?.result && (
          <div className="workflow-last-answer">
            <h3>最近返回</h3>
            <AnswerMarkdown text={last.result.answer} />
          </div>
        )}
        <p className="page-note">
          节点位置可保存于此浏览器；连线与流光不是实时执行 Trace。
        </p>
      </aside>
    </section>
  );
}
