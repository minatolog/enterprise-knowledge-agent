import type { Answer, Source } from "../api";
import { fold } from "./t2s.ts";

const CITATION = /\[资料\s*(\d+)\]/g;

/** Citation numbers in order of first appearance. */
export function citedNumbers(answer: string): number[] {
  const seen: number[] = [];
  for (const match of answer.matchAll(CITATION)) {
    const n = Number(match[1]);
    if (!seen.includes(n)) seen.push(n);
  }
  return seen;
}

/**
 * Map "[资料 N]" (N = position in the retrieved context) to the source that the
 * backend returned for it. The API lists cited sources in order of first
 * citation, so the k-th distinct number maps to sources[k].
 */
export function citationMap(result: Answer): Map<number, Source> {
  const map = new Map<number, Source>();
  citedNumbers(result.answer).forEach((n, index) => {
    const retrieved = result.retrieved?.[n - 1];
    const source = retrieved && result.sources.find((s) => s.chunk_id === retrieved.chunk_id);
    const fallback = result.sources[index];
    if (source || fallback) map.set(n, (source || fallback)!);
  });
  return map;
}

/** Replace citation markers with markdown links the renderer turns into chips. */
export function linkCitations(answer: string): string {
  return answer.replace(CITATION, (_, n) => `[${n}](#cite-${n})`);
}

export function stripCitations(answer: string): string {
  return answer.replace(CITATION, "").replace(/\s+/g, " ").trim();
}

/** Sentences of the answer that cite citation number n. */
export function sentencesCiting(answer: string, n: number): string[] {
  // A citation written after the full stop belongs to the sentence before it.
  const sentences = answer.match(/[^。！？!?\n]+[。！？!?]?(?:\s*\[资料\s*\d+\])*/g) || [];
  return sentences
    .filter((sentence) => new RegExp(`\\[资料\\s*${n}\\]`).test(sentence))
    .map(stripCitations)
    .filter(Boolean);
}

const keep = (ch: string) => /[\p{L}\p{N}]/u.test(ch);

/**
 * Character ranges of `source` that share a run of ≥ minRun characters with any
 * of the `claims`, compared after a Traditional→Simplified fold and ignoring
 * punctuation and spacing. Used to highlight the supporting clause.
 */
export function supportingRanges(source: string, claims: string[], minRun = 7): [number, number][] {
  const positions: number[] = [];
  let folded = "";
  [...source].forEach((ch, index) => {
    if (keep(ch)) {
      folded += fold(ch);
      positions.push(index);
    }
  });
  const chars = [...source];
  const offsets: number[] = [];
  let acc = 0;
  for (const ch of chars) {
    offsets.push(acc);
    acc += ch.length;
  }
  const marked = new Array<boolean>(folded.length).fill(false);
  for (const claim of claims) {
    const target = [...claim].filter(keep).map(fold).join("");
    for (let start = 0; start + minRun <= target.length; start++) {
      const seed = target.slice(start, start + minRun);
      let at = folded.indexOf(seed);
      while (at !== -1) {
        let end = at + minRun;
        let t = start + minRun;
        while (end < folded.length && t < target.length && folded[end] === target[t]) {
          end++;
          t++;
        }
        for (let i = at; i < end; i++) marked[i] = true;
        at = folded.indexOf(seed, at + 1);
      }
    }
  }
  const ranges: [number, number][] = [];
  for (let i = 0; i < marked.length; i++) {
    if (!marked[i]) continue;
    let j = i;
    while (j + 1 < marked.length && marked[j + 1] && positions[j + 1] - positions[j] <= 3) j++;
    ranges.push([offsets[positions[i]], offsets[positions[j]] + chars[positions[j]].length]);
    i = j;
  }
  return ranges;
}

export function pages(source: Pick<Source, "page_start" | "page_end">): string {
  if (!source.page_start) return "";
  return source.page_start === source.page_end ? `第 ${source.page_start} 页` : `第 ${source.page_start}–${source.page_end} 页`;
}

export function documentName(source: Pick<Source, "title" | "source">): string {
  return source.title || source.source.replace(/\.(pdf|docx|md|txt)$/i, "");
}

export function historyFrom(turns: { question: string; result?: Answer }[], limit = 6) {
  return turns
    .filter((turn) => turn.result && turn.result.status !== "refused")
    .slice(-limit)
    .flatMap((turn) => [
      { role: "user" as const, content: turn.question },
      { role: "assistant" as const, content: stripCitations(turn.result!.answer).slice(0, 1200) },
    ]);
}

/** Everything shown in the evidence panel for one answer, and where citation n points. */
export function evidenceOf(result: Answer) {
  const items = result.retrieved?.length ? result.retrieved : result.sources;
  const cited = new Set(result.sources.map((s) => s.chunk_id));
  const map = citationMap(result);
  const indexOfCitation = (n: number) => {
    const source = map.get(n);
    return source ? items.findIndex((item) => item.chunk_id === source.chunk_id) : -1;
  };
  return { items, cited, indexOfCitation };
}

export const REFUSAL_COPY: Record<string, string> = {
  below_rerank_threshold: "最相关的资料也低于拒答线，系统没有调用模型，直接拒答。",
  no_candidates: "你当前可访问的资料里没有检索到相关内容。",
  judge_failed: "模型给出的回答没有通过证据核验，已被拦截。",
  citation_invalid: "模型引用了不存在的资料编号，回答已被拦截。",
};

export function seconds(ms: number | undefined) {
  if (ms === undefined) return "";
  return ms < 1000 ? `${Math.round(ms)} 毫秒` : `${(ms / 1000).toFixed(1)} 秒`;
}
