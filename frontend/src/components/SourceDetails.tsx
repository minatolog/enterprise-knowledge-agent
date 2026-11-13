import { ChevronRight, ExternalLink, FileText, X } from "lucide-react";
import { safeLink, type Answer, type Source } from "../api";
import type { Turn } from "../state/conversations";
export function SourceCitations({
  sources,
  onSelect,
}: {
  sources: Source[];
  onSelect: (source: Source) => void;
}) {
  if (!sources.length)
    return <p className="source-unavailable">此回答未返回可展示的引用来源。</p>;
  return (
    <div className="answer-sources">
      <div className="section-eyebrow">
        引用来源 <span>{sources.length}</span>
      </div>
      <div className="citation-list">
        {sources.map((s) => (
          <button
            className="citation-chip"
            key={s.chunk_id}
            onClick={() => onSelect(s)}
            title={`查看 ${s.source} 的来源详情`}
          >
            <FileText size={14} />
            <span>{s.source}</span>
            <small>
              p. {s.page_start}
              {s.page_end !== s.page_start ? `–${s.page_end}` : ""}
            </small>
            <ChevronRight size={12} />
          </button>
        ))}
      </div>
    </div>
  );
}
export function SourceDetailPanel({
  source,
  onClose,
}: {
  source: Source;
  onClose: () => void;
}) {
  return (
    <aside
      className="source-detail-panel"
      role="dialog"
      aria-modal="true"
      aria-label="来源详情"
    >
      <div className="detail-header">
        <span>
          <FileText size={15} />
          来源详情
        </span>
        <button
          className="icon-btn"
          aria-label="关闭来源详情"
          onClick={onClose}
        >
          <X size={17} />
        </button>
      </div>
      <div className="source-detail-body">
        <div className="document-glyph">
          <FileText size={24} />
        </div>
        <h2>{source.source}</h2>
        <p className="detail-subtitle">来自本次 API 回答的真实引用元数据</p>
        <dl>
          <dt>PDF 页码</dt>
          <dd>
            {source.page_start}
            {source.page_end !== source.page_start ? `–${source.page_end}` : ""}
          </dd>
          <dt>来源路径</dt>
          <dd>
            <code>{source.relative_path || "接口未提供"}</code>
          </dd>
          <dt>Chunk ID</dt>
          <dd>
            <code>{source.chunk_id || "接口未提供"}</code>
          </dd>
          {source.section && (
            <>
              <dt>章节</dt>
              <dd>{source.section}</dd>
            </>
          )}
          <dt>来源标签</dt>
          <dd>{source.label || "接口未提供"}</dd>
        </dl>
        {safeLink(source.source_url) ? (
          <a
            className="button open-original"
            target="_blank"
            rel="noreferrer"
            href={safeLink(source.source_url)}
          >
            打开官方原文
            <ExternalLink size={14} />
          </a>
        ) : (
          <p className="field-missing">当前来源未返回可用的官方原文链接。</p>
        )}
        <div className="source-note">
          <strong>证据原文</strong>
          <p>
            当前问答接口未返回 retrieved text / snippet
            字段，无法在此展示片段正文。
          </p>
        </div>
      </div>
    </aside>
  );
}
export function RetrievalDetailsPanel({ answer }: { answer: Answer }) {
  const missing = [
    "BM25 分路结果与分数",
    "向量检索分路结果与距离",
    "RRF 融合排名与得分",
    "重排前后候选列表",
    "检索片段正文 / snippet",
  ];
  return (
    <details className="retrieval-details">
      <summary>
        <span>检索与技术详情</span>
        <ChevronRight size={13} />
      </summary>
      <div className="retrieval-content">
        <dl>
          <dt>Request ID</dt>
          <dd>
            <code>{answer.request_id}</code>
          </dd>
          <dt>返回候选数量</dt>
          <dd>{answer.retrieval_count}</dd>
          {answer.rerank_score != null && (
            <>
              <dt>返回的最高重排分数</dt>
              <dd>
                {answer.rerank_score.toFixed(4)}
                <span className="muted-text"> · 原始模型分数，不是置信度</span>
              </dd>
            </>
          )}
        </dl>
        <h4>阶段耗时</h4>
        <div className="timing-list">
          {Object.entries(answer.timings_ms).map(([stage, ms]) => (
            <div key={stage}>
              <span>{stage}</span>
              <code>{ms.toFixed(1)} ms</code>
            </div>
          ))}
        </div>
        <h4>最终引用与 Cross-Encoder 分数</h4>
        {answer.sources.map((s) => (
          <div className="source-score" key={s.chunk_id}>
            <span>
              {s.source} · p. {s.page_start}
              {s.page_start !== s.page_end ? `–${s.page_end}` : ""}
            </span>
            <code>
              {s.rerank_score == null ? "未返回" : s.rerank_score.toFixed(4)}
            </code>
          </div>
        ))}
        <div className="missing-fields">
          <h4>当前 v1 接口未暴露</h4>
          <ul>
            {missing.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p>架构具备相关检索步骤，但界面不能据此生成不存在的运行数据。</p>
        </div>
      </div>
    </details>
  );
}
export function RunDetails({
  turn,
  onSource,
}: {
  turn: Turn;
  onSource: (source: Source) => void;
}) {
  return (
    <>
      {turn.error ? (
        <div className="request-error">{turn.error}</div>
      ) : (
        turn.result && (
          <>
            <SourceCitations
              sources={turn.result.sources}
              onSelect={onSource}
            />
            <RetrievalDetailsPanel answer={turn.result} />
          </>
        )
      )}
    </>
  );
}
