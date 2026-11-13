import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowUpRight,
  Check,
  Copy,
  FileSearch,
  GitBranch,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  SquareLibrary,
} from "lucide-react";
import { safeLink, type Source } from "../api";
import type { Conversation, Turn } from "../state/conversations";
import MessageComposer from "./MessageComposer";
import { RetrievalDetailsPanel, SourceCitations } from "./SourceDetails";
const suggestions = [
  {
    icon: ShieldCheck,
    label: "公司有哪些主要合规要求？",
    text: "What are the company's major compliance requirements?",
  },
  {
    icon: SquareLibrary,
    label: "概述公司的治理结构",
    text: "Summarize the corporate governance structure.",
  },
  {
    icon: GitBranch,
    label: "董事会的核心职责是什么？",
    text: "What are the key responsibilities of the board of directors?",
  },
  {
    icon: FileSearch,
    label: "查找内部控制相关规定",
    text: "Find the relevant provisions concerning internal controls.",
  },
];
export function AnswerMarkdown({ text }: { text: string }) {
  return (
    <div className="answer-markdown">
      <Markdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        urlTransform={(url) => safeLink(url) || ""}
        components={{
          a: ({ href, children }) =>
            href ? (
              <a href={href} target="_blank" rel="noreferrer">
                {children}
                <ArrowUpRight size={11} />
              </a>
            ) : (
              <span>{children}</span>
            ),
          img: () => null,
        }}
      >
        {text}
      </Markdown>
    </div>
  );
}
function CopyAnswer({ answer }: { answer: string }) {
  const [state, setState] = useState<"idle" | "copied" | "error">("idle");
  useEffect(() => {
    if (state === "idle") return;
    const timer = setTimeout(() => setState("idle"), 2500);
    return () => clearTimeout(timer);
  }, [state]);
  return (
    <button
      className="answer-action"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(answer);
          setState("copied");
        } catch {
          setState("error");
        }
      }}
      title="复制完整回答"
    >
      {state === "copied" ? <Check size={14} /> : <Copy size={14} />}
      {state === "copied"
        ? "已复制"
        : state === "error"
          ? "复制失败，请手动选择"
          : "复制"}
    </button>
  );
}
export function AssistantMessage({
  turn,
  pending,
  onRegenerate,
  onSource,
}: {
  turn: Turn;
  pending: boolean;
  onRegenerate: () => void;
  onSource: (s: Source) => void;
}) {
  return (
    <article className="chat-turn">
      <div className="user-message">
        <span className="visually-hidden">你：</span>
        {turn.question}
      </div>
      <div className="assistant-message">
        <div className="assistant-label">
          <span className="assistant-mini-mark">C</span>CNOOC 知识助手
          <span className="response-time">
            {new Date(turn.createdAt).toLocaleTimeString("zh-CN", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
        {turn.result ? (
          <>
            <AnswerMarkdown text={turn.result.answer} />
            <SourceCitations
              sources={turn.result.sources}
              onSelect={onSource}
            />
            <div className="answer-actions">
              <CopyAnswer answer={turn.result.answer} />
              <button
                className="answer-action"
                disabled={pending}
                title="以相同问题重新调用问答接口"
                onClick={onRegenerate}
              >
                <RefreshCw size={14} />
                重新生成
              </button>
              <span>
                {turn.result.timings_ms.total_ms != null
                  ? `${(turn.result.timings_ms.total_ms / 1000).toFixed(1)} 秒`
                  : ""}
              </span>
            </div>
            <RetrievalDetailsPanel answer={turn.result} />
          </>
        ) : (
          <div className="request-error" role="alert">
            <strong>本次请求未完成</strong>
            <p>{turn.error}</p>
            <button disabled={pending} onClick={onRegenerate}>
              <RefreshCw size={13} />
              重试此问题
            </button>
          </div>
        )}
      </div>
    </article>
  );
}
interface Props {
  conversation: Conversation;
  draft: string;
  onDraft: (value: string) => void;
  onSend: () => void;
  onRegenerate: (turn: Turn) => void;
  pending: {
    conversationId: string;
    question: string;
    replacing?: string;
  } | null;
  onSource: (source: Source) => void;
  topK: number;
  onTopK: (value: number) => void;
}
export default function Chat(p: Props) {
  const scroller = useRef<HTMLDivElement>(null),
    tail = useRef<HTMLDivElement>(null),
    follow = useRef(true);
  const pendingHere = p.pending?.conversationId === p.conversation.id;
  useEffect(() => {
    follow.current = true;
    if (scroller.current)
      scroller.current.scrollTop = scroller.current.scrollHeight;
  }, [p.conversation.id]);
  useEffect(() => {
    const el = scroller.current;
    if (el && follow.current)
      el.scrollTo({ top: el.scrollHeight, behavior: "auto" });
  }, [p.conversation.turns, pendingHere]);
  const empty = !p.conversation.turns.length && !pendingHere;
  const composer = (
    <MessageComposer
      value={p.draft}
      onChange={p.onDraft}
      onSend={p.onSend}
      pending={Boolean(p.pending)}
      topK={p.topK}
      onTopK={p.onTopK}
    />
  );
  return (
    <section
      className={`chat-layout ${empty ? "empty-chat" : ""}`}
      aria-label="知识问答"
    >
      <div
        className="message-scroll"
        ref={scroller}
        onScroll={(e) => {
          const el = e.currentTarget;
          follow.current =
            el.scrollHeight - el.scrollTop - el.clientHeight < 100;
        }}
      >
        <div className="chat-column">
          {empty ? (
            <div className="welcome-screen">
              <div className="welcome-kicker">
                <span />
                CNOOC ENTERPRISE KNOWLEDGE
              </div>
              <h1>
                让每一个答案，
                <br />
                <span>都有据可循。</span>
              </h1>
              <p>
                从中国海油官方资料中检索、理解并回答。
                <br />
                把复杂的制度问题，变成清晰、可追溯的答案。
              </p>
              {composer}
              <div className="suggested-questions" aria-label="建议问题">
                {suggestions.map((s) => (
                  <button
                    key={s.text}
                    onClick={() => p.onDraft(s.text)}
                    title={s.text}
                  >
                    <s.icon size={16} />
                    <span>{s.label}</span>
                    <ArrowUpRight size={13} />
                  </button>
                ))}
              </div>
              <div className="welcome-footnote">
                <ShieldCheck size={13} />
                官方资料 · 混合检索 · 原文引用
              </div>
            </div>
          ) : (
            <>
              <div className="conversation-start">
                CNOOC 官方知识库 <span>每次提问独立检索</span>
              </div>
              {p.conversation.turns.map((turn) => (
                <AssistantMessage
                  key={turn.id}
                  turn={turn}
                  pending={Boolean(p.pending)}
                  onSource={p.onSource}
                  onRegenerate={() => p.onRegenerate(turn)}
                />
              ))}
              {pendingHere && (
                <div className="pending-message" role="status">
                  {!p.pending?.replacing && (
                    <div className="user-message">{p.pending?.question}</div>
                  )}
                  <div className="thinking-row">
                    <LoaderCircle size={16} className="spin" />
                    <span>
                      {p.pending?.replacing
                        ? "正在重新请求回答…"
                        : "正在检索官方资料并生成回答…"}
                    </span>
                    <span className="thinking-dots">
                      <i />
                      <i />
                      <i />
                    </span>
                  </div>
                </div>
              )}
              <div ref={tail} />
            </>
          )}
        </div>
      </div>
      {!empty && (
        <div className="fixed-composer">
          <div className="chat-column">{composer}</div>
        </div>
      )}
    </section>
  );
}
