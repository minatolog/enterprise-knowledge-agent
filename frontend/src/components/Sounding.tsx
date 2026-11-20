import type { Source } from "../api";

const FLOOR = -3; // log10 of the weakest score drawn (0.001)

function depth(score: number | null | undefined) {
  if (score === null || score === undefined || !Number.isFinite(score)) return 0;
  return Math.min(1, Math.max(0, (Math.log10(Math.max(score, 10 ** FLOOR)) - FLOOR) / -FLOOR));
}

/**
 * Evidence sounding: one bar per retrieved chunk, height = reranker score on a
 * log scale, with the refusal line (RAG_MIN_RERANK_SCORE) drawn across.
 */
export default function Sounding({
  retrieved,
  cited,
  threshold,
  onPick,
}: {
  retrieved: Source[];
  cited: Set<string>;
  threshold: number | null | undefined;
  onPick: (index: number) => void;
}) {
  const scored = retrieved.filter((s) => s.rerank_score !== null && s.rerank_score !== undefined);
  if (!scored.length) return null;
  const height = 56;
  const line = threshold ? height - depth(threshold) * height : null;
  const below = threshold ? scored.filter((s) => (s.rerank_score ?? 0) < threshold).length : 0;
  return (
    <figure className="sounding">
      <figcaption>
        证据强度
        <span>
          {retrieved.length} 段资料，{cited.size} 段被引用
          {threshold ? `，${below} 段低于拒答线 ${threshold}` : ""}
        </span>
      </figcaption>
      <div className="sounding-plot" style={{ height }}>
        {line !== null && (
          <div className="sounding-line" style={{ top: line }} aria-hidden="true">
            <span>拒答线</span>
          </div>
        )}
        {retrieved.map((source, index) => {
          const value = depth(source.rerank_score);
          const isCited = cited.has(source.chunk_id);
          const weak = threshold ? (source.rerank_score ?? 0) < threshold : false;
          return (
            <button
              key={source.chunk_id}
              className={`sounding-bar${isCited ? " is-cited" : ""}${weak ? " is-weak" : ""}`}
              style={{ height: `${Math.max(6, value * 100)}%` }}
              onClick={() => onPick(index)}
              aria-label={`资料 ${index + 1}，分数 ${source.rerank_score?.toFixed(3)}${isCited ? "，已引用" : ""}`}
              title={`资料 ${index + 1}：${source.rerank_score?.toFixed(3)}${isCited ? "（已引用）" : ""}`}
            >
              <span>{index + 1}</span>
            </button>
          );
        })}
      </div>
    </figure>
  );
}
