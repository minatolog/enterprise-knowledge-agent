export interface Source {
  chunk_id: string;
  source: string;
  relative_path: string;
  page_start: number;
  page_end: number;
  source_url: string | null;
  label: string;
  rerank_score: number | null;
  section?: string;
}
export interface Answer {
  request_id: string;
  answer: string;
  sources: Source[];
  retrieval_count: number;
  rerank_score?: number | null;
  timings_ms: Record<string, number>;
}
export interface DocumentInfo {
  source: string;
  relative_path: string;
  chunk_count: number;
  page_start: number;
  page_end: number;
  source_url: string | null;
  knowledge_base?: string | null;
}
export interface DocumentList {
  collection: string;
  indexed_document_count: number;
  indexed_chunk_count: number;
  documents: DocumentInfo[];
}
export async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(path, options);
  let body;
  try {
    body = await response.json();
  } catch {
    throw new Error("服务未返回有效 JSON，请检查本地 API。");
  }
  if (!response.ok)
    throw new Error(
      `${body.message || "请求失败"}${body.request_id ? ` · request_id: ${body.request_id}` : ""}`,
    );
  return body;
}
export function safeLink(value: string | null | undefined): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}
export const api = {
  health: () => request<{ status: string }>("/health"),
  documents: () => request<DocumentList>("/api/v1/documents"),
  query: (question: string, topK: number, signal: AbortSignal) =>
    request<Answer>("/api/v1/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k: topK }),
      signal,
    }),
};
