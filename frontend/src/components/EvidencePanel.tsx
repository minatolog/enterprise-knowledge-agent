import { useEffect, useRef, useState } from "react";
import { ExternalLink, X } from "lucide-react";
import { api, safeLink, type Answer, type Connection, type Source } from "../api";
import { documentName, evidenceOf, pages, sentencesCiting, supportingRanges } from "../utils/evidence";

function Highlighted({ text, ranges }: { text: string; ranges: [number, number][] }) {
  if (!ranges.length) return <>{text}</>;
  const parts: React.ReactNode[] = [];
  let at = 0;
  ranges.forEach(([start, end], index) => {
    if (start > at) parts.push(text.slice(at, start));
    parts.push(<mark key={index}>{text.slice(start, end)}</mark>);
    at = end;
  });
  parts.push(text.slice(at));
  return <>{parts}</>;
}

function OpenOriginal({ source, connection }: { source: Source; connection: Connection }) {
  const [error, setError] = useState("");
  const external = safeLink(source.source_url);
  if (external) {
    const href = source.page_start ? `${external.split("#")[0]}#page=${source.page_start}` : external;
    return (
      <a className="text-button" href={href} target="_blank" rel="noreferrer">
        <ExternalLink size={14} /> 打开原文
      </a>
    );
  }
  if (source.source_url?.startsWith("/api/v2/"))
    return (
      <>
        <button
          className="text-button"
          onClick={async () => {
            try {
              setError("");
              window.open(await api.original(connection, source.source_url!), "_blank", "noopener");
            } catch (e) {
              setError((e as Error).message);
            }
          }}
        >
          <ExternalLink size={14} /> 下载此版本原文
        </button>
        {error && <span className="field-error">{error}</span>}
      </>
    );
  return null;
}

export default function EvidencePanel({
  result,
  index,
  onSelect,
  onClose,
  connection,
}: {
  result: Answer;
  index: number;
  onSelect: (index: number) => void;
  onClose: () => void;
  connection: Connection;
}) {
  const { items, cited, indexOfCitation } = evidenceOf(result);
  const panel = useRef<HTMLElement>(null);
  const current = items[index];
  const citation = [...Array(items.length).keys()].map((i) => i + 1).find((n) => indexOfCitation(n) === index);
  const claims = citation ? sentencesCiting(result.answer, citation) : [];
  const text = current?.text || "";
  const ranges = text && claims.length ? supportingRanges(text, claims) : [];

  useEffect(() => {
    panel.current?.querySelector<HTMLElement>(".evidence-current")?.focus();
  }, [index, result.request_id]);

  return (
    <aside className="evidence" ref={panel} aria-label="引用原文">
      <header className="evidence-head">
        <h2>原文</h2>
        <button className="icon-button" onClick={onClose} aria-label="关闭原文栏">
          <X size={18} />
        </button>
      </header>
      {current && (
        <section className="evidence-current" tabIndex={-1}>
          <p className="evidence-doc">{documentName(current)}</p>
          <p className="evidence-where">
            {[current.section, pages(current)].filter(Boolean).join("，")}
          </p>
          {text ? (
            <blockquote className="evidence-text">
              <Highlighted text={text} ranges={ranges} />
            </blockquote>
          ) : (
            <p className="evidence-missing">这条记录没有保存原文片段，请打开原文查看。</p>
          )}
          <div className="evidence-foot">
            <span className={cited.has(current.chunk_id) ? "evidence-cited" : "evidence-uncited"}>
              {citation ? `回答中的第 ${citation} 条引用` : cited.has(current.chunk_id) ? "被回答引用" : "检索到但未被引用"}
            </span>
            {current.rerank_score !== null && <span className="score">相关度 {current.rerank_score.toFixed(3)}</span>}
            <OpenOriginal source={current} connection={connection} />
          </div>
          {ranges.length > 0 && <p className="evidence-note">黄色标出的是与回答文字重合的原文，供人工核对。</p>}
        </section>
      )}
      {items.length > 1 && (
        <section className="evidence-list">
          <h3>本次检索到的其他资料</h3>
          <ol>
            {items.map((item, i) =>
              i === index ? null : (
                <li key={item.chunk_id}>
                  <button onClick={() => onSelect(i)}>
                    <span className="evidence-list-name">{documentName(item)}</span>
                    <span className="evidence-list-where">
                      {pages(item)}
                      {cited.has(item.chunk_id) ? "，已引用" : ""}
                    </span>
                  </button>
                </li>
              ),
            )}
          </ol>
        </section>
      )}
    </aside>
  );
}
