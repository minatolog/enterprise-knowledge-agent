import { useEffect, useRef } from "react";
import { ArrowUp, BookOpen, LoaderCircle } from "lucide-react";
interface Props {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  pending: boolean;
  topK: number;
  onTopK: (value: number) => void;
  compact?: boolean;
}
export default function MessageComposer(p: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (ref.current) {
      ref.current.style.height = "auto";
      ref.current.style.height = Math.min(ref.current.scrollHeight, 180) + "px";
    }
  }, [p.value]);
  return (
    <form
      className={`message-composer ${p.compact ? "compact" : ""}`}
      onSubmit={(e) => {
        e.preventDefault();
        p.onSend();
      }}
    >
      <div className="composer-box">
        <label
          className="visually-hidden"
          htmlFor={p.compact ? "flow-question" : "chat-question"}
        >
          输入问题
        </label>
        <textarea
          ref={ref}
          id={p.compact ? "flow-question" : "chat-question"}
          placeholder="向 CNOOC 企业知识库提问…"
          value={p.value}
          onChange={(e) => p.onChange(e.target.value)}
          maxLength={2000}
          disabled={p.pending}
          rows={2}
          onKeyDown={(e) => {
            if (
              e.key === "Enter" &&
              !e.shiftKey &&
              !e.nativeEvent.isComposing
            ) {
              e.preventDefault();
              if (!p.pending) p.onSend();
            }
          }}
        />
        <div className="composer-tools">
          <span className="knowledge-scope">
            <BookOpen size={13} />
            官方知识库
          </span>
          <label className="topk-selector">
            <span className="visually-hidden">返回片段数量</span>
            <select
              aria-label="返回片段数量"
              value={p.topK}
              onChange={(e) => p.onTopK(Number(e.target.value))}
              disabled={p.pending}
            >
              <option value={3}>Top 3</option>
              <option value={5}>Top 5</option>
              <option value={8}>Top 8</option>
            </select>
          </label>
          <button
            type="submit"
            className="send-question"
            aria-label="发送问题"
            disabled={p.pending || !p.value.trim()}
          >
            {p.pending ? (
              <LoaderCircle size={17} className="spin" />
            ) : (
              <ArrowUp size={19} />
            )}
          </button>
        </div>
      </div>
      <p className="composer-disclaimer">
        Enter 发送 · Shift + Enter 换行
        <span>回答仅供参考，请核对来源原文。</span>
      </p>
    </form>
  );
}
