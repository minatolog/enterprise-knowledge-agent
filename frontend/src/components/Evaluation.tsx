import { useEffect, useState } from "react";
import { api, type EvalReport } from "../api";

const METHOD_NAMES: Record<string, string> = {
  dense: "仅向量检索",
  bm25: "仅关键词检索（BM25）",
  hybrid_rrf: "混合检索（RRF 融合）",
  hybrid_rrf_reranker: "混合检索 + 重排（线上配置）",
};

const REASONS: Record<string, string> = {
  no_expected_evidence_in_top_10: "前 10 段都没有命中证据",
  partial_expected_evidence_missing: "只召回了部分证据",
  no_expected_chunk_in_top_10: "前 10 段都没有命中证据",
  partial_expected_chunks_missing: "只召回了部分证据",
};

const pct = (v: number) => `${Math.round(v * 1000) / 10}%`;

function Bar({ value }: { value: number }) {
  return (
    <span className="metric">
      <span className="metric-track"><span className="metric-bar" style={{ width: `${value * 100}%` }} /></span>
      <span className="metric-value">{pct(value)}</span>
    </span>
  );
}

function Sweep({ rows, current }: { rows: EvalReport["threshold_sweep"]; current: number }) {
  if (!rows.length) return null;
  const w = 560, h = 180, pad = 40;
  const x = (i: number) => pad + (i / (rows.length - 1)) * (w - pad * 2);
  const y = (v: number) => h - pad - v * (h - pad * 1.6);
  const path = (key: "answerable_kept_with_hit" | "abstention_refused") =>
    rows.map((row, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(row[key]).toFixed(1)}`).join(" ");
  const currentIndex = rows.findIndex((row) => row.threshold === current);
  return (
    <figure className="sweep">
      <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label="拒答线取值与有答案题保留率、无答案题拒答率的关系">
        {[0, 0.5, 1].map((v) => (
          <g key={v}>
            <line x1={pad} x2={w - pad} y1={y(v)} y2={y(v)} className="sweep-grid" />
            <text x={pad - 6} y={y(v) + 4} textAnchor="end" className="sweep-axis">{v * 100}%</text>
          </g>
        ))}
        {currentIndex >= 0 && <line x1={x(currentIndex)} x2={x(currentIndex)} y1={pad * 0.4} y2={h - pad} className="sweep-current" />}
        <path d={path("answerable_kept_with_hit")} className="sweep-kept" />
        <path d={path("abstention_refused")} className="sweep-refused" />
        {rows.map((row, i) => (
          <text key={row.threshold} x={x(i)} y={h - pad + 16} textAnchor="middle" className="sweep-axis">{row.threshold}</text>
        ))}
      </svg>
      <figcaption>
        <span className="key key-kept">有答案题：保留且答案在前几段</span>
        <span className="key key-refused">无答案题：被拒答</span>
        {currentIndex >= 0 && <span className="key key-current">当前拒答线 {current}</span>}
      </figcaption>
    </figure>
  );
}

export default function Evaluation() {
  const [report, setReport] = useState<EvalReport | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api.evaluation().then(setReport).catch((e) => setError(e.message));
  }, []);
  const run = report?.run || {};
  const threshold = Number(run.min_rerank_score ?? 0);
  return (
    <div className="page">
      <header className="page-head">
        <h1>检索评测</h1>
      </header>
      {error && (
        <div className="notice notice-warn">
          <p>{error}</p>
          <p>在项目目录运行 <code>python eval/run_cnooc_eval.py</code> 生成报告，再回到这里查看。</p>
        </div>
      )}
      {report && (
        <>
          <p className="lead">
            用 {String(run.answerable_count ?? "?")} 道有答案题和 {String(run.abstention_count ?? "?")} 道无答案题，比较四种检索方式能否把证据原文排在前面。
            只评检索，不评模型写出的回答。
            {run.relevance === "quote" ? " 只要某段资料完整包含评测集里的证据原文，就算命中，与切分方式无关。" : ""}
          </p>
          <table className="table eval-table">
            <thead>
              <tr>
                <th scope="col">检索方式</th>
                <th scope="col">第 1 段命中</th>
                <th scope="col">前 3 段命中</th>
                <th scope="col">前 10 段召回</th>
                <th scope="col" className="num">MRR</th>
                <th scope="col" className="num">平均耗时</th>
              </tr>
            </thead>
            <tbody>
              {report.summary.map((row) => (
                <tr key={row.method} className={row.method === "hybrid_rrf_reranker" ? "is-served" : ""}>
                  <th scope="row">{METHOD_NAMES[row.method] || row.method}</th>
                  <td><Bar value={row.hit_at_1} /></td>
                  <td><Bar value={row.hit_at_3} /></td>
                  <td><Bar value={row.recall_at_10} /></td>
                  <td className="num">{row.mrr_at_10.toFixed(3)}</td>
                  <td className="num">{Math.round(row.mean_elapsed_ms)} 毫秒</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="footnote">
            切分：{String(run.chunker ?? "page")}；重排候选：{String(run.rerank_candidate_k ?? run.candidate_budget ?? "?")} 段；
            运行于 {String(run.started_at ?? "").slice(0, 16).replace("T", " ")}（UTC）
          </p>

          {report.threshold_sweep.length > 0 && (
            <section className="settings-block">
              <h2>拒答线怎么定</h2>
              <p>拒答线越高，越多无关问题会在调用模型前被拦下，但也会误拒一些本来能回答的问题。两条线交叉附近通常是合理的取值。</p>
              <Sweep rows={report.threshold_sweep} current={threshold} />
            </section>
          )}

          {report.failures.length > 0 && (
            <section className="settings-block">
              <h2>没检索好的题目</h2>
              <ul className="failures">
                {report.failures
                  .filter((f) => f.method === "hybrid_rrf_reranker")
                  .map((f) => (
                    <li key={f.question_id}>
                      <span className="failure-q">{f.question}</span>
                      <span className="failure-why">
                        {REASONS[f.failure_reason] || f.failure_reason}
                        {f.first_relevant_rank ? `，首个相关段排第 ${f.first_relevant_rank}` : ""}
                      </span>
                    </li>
                  ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}
