import { useEffect, useRef, useState } from "react";
import { ArrowUp, Check, Copy, RotateCcw, Square } from "lucide-react";
import type { Assistant } from "../state/useAssistant";
import type { Turn } from "../state/conversations";
import { evidenceOf, REFUSAL_COPY, seconds, stripCitations } from "../utils/evidence";
import AnswerBody from "./AnswerBody";
import Sounding from "./Sounding";

export interface Focus {
  turnId: string;
  index: number;
}

const EXAMPLES = [
  "员工入职时需要签署哪些合规文件？",
  "审核委员会多久至少开一次会，会议文件要提前几天发送？",
  "董事会会议的法定人数和表决规则是什么？",
  "员工离职后在竞业和保密方面还有哪些义务？",
];

const VERIFICATION: Record<string, { label: string; tone: "ok" | "warn" | "muted" }> = {
  judge_passed: { label: "已通过证据核验", tone: "ok" },
  judge_partial: { label: "部分内容未通过核验，已删除", tone: "warn" },
  citation_structure_only: { label: "只检查了引用编号", tone: "muted" },
};

function TurnView({
  turn,
  focus,
  onFocus,
  onRetry,
  busy,
}: {
  turn: Turn;
  focus: Focus | null;
  onFocus: (focus: Focus) => void;
  onRetry: () => void;
  busy: boolean;
}) {
  const [copied, setCopied] = useState(false);
  const result = turn.result;
  const evidence = result ? evidenceOf(result) : null;
  const refused = result?.status === "refused" || result?.refusal_reason;
  const reason = result?.refusal_reason || (result?.verification && REFUSAL_COPY[result.verification] ? result.verification : "");
  const activeCitation =
    focus?.turnId === turn.id && evidence
      ? [...Array(evidence.items.length).keys()].map((i) => i + 1).find((n) => evidence.indexOfCitation(n) === focus.index) ?? null
      : null;
  const timings = result?.timings_ms || {};
  const verification = result?.verification ? VERIFICATION[result.verification] : undefined;

  return (
    <article className="turn">
      <h2 className="turn-question">{turn.question}</h2>
      {turn.error && (
        <div className="notice notice-error" role="alert">
          <p>没有拿到回答：{turn.error}</p>
          <button className="text-button" onClick={onRetry} disabled={busy}>
            <RotateCcw size={14} /> 重新提问
          </button>
        </div>
      )}
      {result && refused && (
        <div className="refusal">
          <p className="refusal-title">知识库里没有足够依据回答这个问题。</p>
          <p>{REFUSAL_COPY[reason] || result.answer}</p>
          {result.refusal_reason === "below_rerank_threshold" && result.rerank_score !== undefined && result.rerank_score !== null && (
            <p className="refusal-detail">
              最相关资料得分 {result.rerank_score.toFixed(3)}，拒答线 {result.min_rerank_score}。可以换个说法，或在“知识库”确认这类文件是否已收录。
            </p>
          )}
        </div>
      )}
      {result && !refused && (
        <AnswerBody text={result.answer} activeCitation={activeCitation} onCite={(n) => {
          const index = evidence!.indexOfCitation(n);
          if (index >= 0) onFocus({ turnId: turn.id, index });
        }} />
      )}
      {result && evidence && evidence.items.length > 0 && (
        <Sounding
          retrieved={evidence.items}
          cited={evidence.cited}
          threshold={result.min_rerank_score}
          onPick={(index) => onFocus({ turnId: turn.id, index })}
        />
      )}
      {result && (
        <footer className="turn-meta">
          {verification && <span className={`badge badge-${verification.tone}`}>{verification.label}</span>}
          {result.cached && <span className="badge badge-muted">来自缓存</span>}
          {result.search_query && result.search_query !== turn.question && (
            <span className="rewrite">按上文理解为：{result.search_query}</span>
          )}
          <span className="timing">
            用时 {seconds(timings.total_ms)}
            {timings.llm_ms ? `，其中生成 ${seconds(timings.llm_ms)}` : ""}
          </span>
          <span className="turn-actions">
            {!refused && (
              <button
                className="text-button"
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(stripCitations(result.answer));
                    setCopied(true);
                    setTimeout(() => setCopied(false), 1600);
                  } catch {
                    /* Clipboard unavailable. */
                  }
                }}
              >
                {copied ? <Check size={14} /> : <Copy size={14} />} {copied ? "已复制" : "复制"}
              </button>
            )}
            <button className="text-button" onClick={onRetry} disabled={busy}>
              <RotateCcw size={14} /> 重新回答
            </button>
          </span>
        </footer>
      )}
    </article>
  );
}

export default function Ask({
  assistant,
  focus,
  onFocus,
}: {
  assistant: Assistant;
  focus: Focus | null;
  onFocus: (focus: Focus) => void;
}) {
  const [draft, setDraft] = useState("");
  const input = useRef<HTMLTextAreaElement>(null);
  const end = useRef<HTMLDivElement>(null);
  const { active, pending } = assistant;
  const thisPending = pending?.conversationId === active.id ? pending : null;
  const docs = assistant.documents;

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [active.turns.length, thisPending]);

  useEffect(() => {
    input.current?.focus();
  }, [active.id]);

  const needsToken = assistant.prefs.mode === "enterprise" && !assistant.token.trim();
  const submit = (text = draft) => {
    if (!text.trim() || pending || needsToken) return;
    setDraft("");
    void assistant.send(text);
  };

  return (
    <div className="ask">
      <div className="ask-scroll">
        {active.turns.length === 0 && !thisPending ? (
          <section className="welcome">
            <h1>查一条制度，连同原文一起看。</h1>
            <p>
              {assistant.prefs.mode === "enterprise"
                ? "回答只来自你有权限查看的企业资料；每句话后面的编号可以打开对应原文。"
                : docs
                  ? `当前收录 ${docs.indexed_document_count} 份文件，共 ${docs.indexed_chunk_count} 段：员工合规手册、董事及高管道德守则、组织章程细则和四个董事会委员会章程。年报和 ESG 报告不在范围内。`
                  : "回答只来自已收录的公开制度文件；每句话后面的编号可以打开对应原文。"}
            </p>
            <ul className="examples">
              {EXAMPLES.map((example) => (
                <li key={example}>
                  <button onClick={() => submit(example)} disabled={Boolean(pending) || needsToken}>
                    {example}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ) : (
          <div className="turns">
            {active.turns.map((turn) => (
              <TurnView
                key={turn.id}
                turn={turn}
                focus={focus}
                onFocus={onFocus}
                busy={Boolean(pending)}
                onRetry={() => void assistant.send(turn.question, turn.id)}
              />
            ))}
            {thisPending && (
              <article className="turn is-pending" aria-live="polite">
                <h2 className="turn-question">{thisPending.question}</h2>
                <div className="pending">
                  <span className="pending-wave" aria-hidden="true" />
                  正在检索资料并核对原文
                </div>
              </article>
            )}
          </div>
        )}
        <div ref={end} />
      </div>

      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        {needsToken && (
          <p className="composer-block" role="status">
            当前是企业知识库，还没有填写令牌。<a href="#settings">去设置</a>填写令牌，或切换回本地知识库。
          </p>
        )}
        <label htmlFor="question" className="visually-hidden">
          输入问题
        </label>
        <textarea
          id="question"
          ref={input}
          rows={1}
          value={draft}
          maxLength={2000}
          placeholder={active.turns.length ? "接着问，或换一个问题" : "例如：员工可以接受供应商的礼品吗？"}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault();
              submit();
            }
          }}
        />
        <div className="composer-bar">
          <label className="topk">
            引用资料
            <select value={assistant.prefs.topK} onChange={(event) => assistant.setPrefs({ topK: Number(event.target.value) })}>
              {[3, 5, 8].map((value) => (
                <option key={value} value={value}>
                  {value} 段
                </option>
              ))}
            </select>
          </label>
          <span className="composer-hint">Enter 发送，Shift + Enter 换行</span>
          {pending ? (
            <button type="button" className="send is-stop" onClick={assistant.stop}>
              <Square size={14} /> 停止
            </button>
          ) : (
            <button type="submit" className="send" disabled={!draft.trim() || needsToken}>
              <ArrowUp size={16} /> 提问
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
