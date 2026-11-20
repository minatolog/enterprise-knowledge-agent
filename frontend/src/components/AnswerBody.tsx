import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { safeLink } from "../api";
import { linkCitations } from "../utils/evidence";

export default function AnswerBody({
  text,
  onCite,
  activeCitation,
}: {
  text: string;
  onCite: (n: number) => void;
  activeCitation?: number | null;
}) {
  return (
    <div className="answer-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a({ href, children }) {
            const cite = href?.match(/^#cite-(\d+)$/);
            if (cite) {
              const n = Number(cite[1]);
              return (
                <button
                  className={`cite${activeCitation === n ? " is-active" : ""}`}
                  onClick={() => onCite(n)}
                  aria-label={`查看资料 ${n}`}
                >
                  {n}
                </button>
              );
            }
            const link = safeLink(href);
            return link ? (
              <a href={link} target="_blank" rel="noreferrer">
                {children}
              </a>
            ) : (
              <>{children}</>
            );
          },
          img: () => null,
        }}
      >
        {linkCitations(text)}
      </ReactMarkdown>
    </div>
  );
}
