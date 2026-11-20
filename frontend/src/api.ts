export type Mode = "local" | "enterprise";

export interface Connection {
  mode: Mode;
  token: string;
}

export interface Source {
  chunk_id: string;
  source: string;
  title?: string | null;
  relative_path: string;
  page_start: number;
  page_end: number;
  source_url: string | null;
  label: string;
  rerank_score: number | null;
  section?: string;
  text?: string;
}

export interface Answer {
  request_id: string;
  answer: string;
  sources: Source[];
  retrieval_count: number;
  rerank_score?: number | null;
  timings_ms: Record<string, number>;
  status?: "answered" | "refused";
  refusal_reason?: string | null;
  search_query?: string | null;
  min_rerank_score?: number | null;
  retrieved?: Source[];
  verification?: string;
  unsupported_claims?: string[];
  cached?: boolean;
  release_id?: string;
}

export interface DocumentInfo {
  source: string;
  title?: string | null;
  chunker?: string | null;
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

export interface ServiceConfig {
  collection: string;
  embedding_model: string;
  reranker_model: string;
  llm_model: string;
  llm_configured: boolean;
  chunker: string;
  index_format: string;
  default_top_k: number;
  max_top_k: number;
  candidate_k: number;
  min_rerank_score: number;
  t2s_backend: string;
}

export interface EvalSummary {
  method: string;
  hit_at_1: number;
  hit_at_3: number;
  hit_at_5: number;
  hit_at_10: number;
  recall_at_10: number;
  mrr_at_10: number;
  mean_elapsed_ms: number;
  failure_count: number;
}

export interface EvalReport {
  run: Record<string, unknown>;
  summary: EvalSummary[];
  threshold_sweep: {
    threshold: number;
    answerable_kept: number;
    answerable_kept_with_hit: number;
    abstention_refused: number;
  }[];
  abstention?: { question_id: string; question: string; top_rerank_score: number | null }[] | null;
  failures: {
    method: string;
    question_id: string;
    question: string;
    category: string;
    first_relevant_rank: number | null;
    failure_reason: string;
  }[];
}

export interface Me {
  subject: string;
  tenant: string;
  groups: string[];
  roles: string[];
}

export interface ManagedDocument {
  id: string;
  title: string;
  version: number;
  groups: string[];
  status: "published" | "pending" | "failed";
  published_version: number | null;
}

export interface Release {
  id: string;
  created: number;
  documents: number;
  chunks: number | null;
  reused: number | null;
  embedded: number | null;
  format: string | null;
  failures: { document_id: string; title: string; error: string; message: string }[];
}

export interface Job {
  id: string;
  status: "queued" | "running" | "succeeded" | "failed";
  attempts: number;
  error: string | null;
  release_id: string | null;
}

export class ApiError extends Error {
  readonly status: number;
  readonly requestId?: string;
  constructor(message: string, status: number, requestId?: string) {
    super(message);
    this.status = status;
    this.requestId = requestId;
  }
}

function authHeaders(connection?: Connection): Record<string, string> {
  return connection?.mode === "enterprise" && connection.token.trim()
    ? { Authorization: `Bearer ${connection.token.trim()}` }
    : {};
}

const STATUS_HINTS: Record<number, string> = {
  401: "企业令牌无效或已过期，请在“设置”里更新令牌。",
  403: "当前账号没有执行这个操作的权限。",
  404: "服务里没有找到这项内容。",
  413: "文件超过上传大小限制。",
  415: "不支持这种文件类型，请上传 PDF、DOCX、Markdown 或 TXT。",
  503: "服务暂时不可用，请检查模型密钥或索引是否就绪。",
};

export const ENTERPRISE_NO_TOKEN = "企业知识库需要令牌。请到“设置”里填写令牌，或切换回本地知识库。";
export const ENTERPRISE_MISSING =
  "当前打开的服务没有企业接口（/api/v2）。用 start-studio.command 启动的是本地服务，请到“设置”里切换回本地知识库；要使用企业知识库，需要启动 app.enterprise.api。";

export async function request<T>(path: string, options: RequestInit = {}, connection?: Connection): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...options,
      headers: { ...authHeaders(connection), ...(options.headers || {}) },
    });
  } catch (error) {
    if ((error as Error).name === "AbortError") throw error;
    throw new ApiError("无法连接到服务。请确认后端已经启动。", 0);
  }
  let body: Record<string, unknown> = {};
  try {
    body = await response.json();
  } catch {
    if (!response.ok) throw new ApiError(STATUS_HINTS[response.status] || `请求失败（HTTP ${response.status}）`, response.status);
    throw new ApiError("服务返回的内容不是 JSON。", response.status);
  }
  if (!response.ok) {
    const detail = typeof body.message === "string" ? body.message : typeof body.detail === "string" ? body.detail : "";
    const message = STATUS_HINTS[response.status] && !detail.match(/[一-鿿]/) ? STATUS_HINTS[response.status] : detail || `请求失败（HTTP ${response.status}）`;
    throw new ApiError(message, response.status, typeof body.request_id === "string" ? body.request_id : undefined);
  }
  return body as T;
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

export interface HistoryTurn {
  role: "user" | "assistant";
  content: string;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  config: () => request<ServiceConfig>("/api/v1/config"),
  evaluation: () => request<EvalReport>("/api/v1/eval/latest"),
  documents: () => request<DocumentList>("/api/v1/documents"),
  async query(
    connection: Connection,
    input: { question: string; topK: number; history: HistoryTurn[]; sessionId: string },
    signal: AbortSignal,
  ) {
    const json = { "Content-Type": "application/json" };
    if (connection.mode === "enterprise") {
      if (!connection.token.trim()) throw new ApiError(ENTERPRISE_NO_TOKEN, 401);
      try {
        return await request<Answer>(
          "/api/v2/query",
          { method: "POST", headers: json, signal, body: JSON.stringify({ question: input.question, top_k: input.topK, session_id: input.sessionId }) },
          connection,
        );
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) throw new ApiError(ENTERPRISE_MISSING, 404);
        throw error;
      }
    }
    return request<Answer>("/api/v1/query", {
      method: "POST",
      headers: json,
      signal,
      body: JSON.stringify({ question: input.question, top_k: input.topK, history: input.history }),
    });
  },
  me: (c: Connection) => request<Me>("/api/v2/me", {}, c),
  managedDocuments: (c: Connection) => request<ManagedDocument[]>("/api/v2/documents", {}, c),
  upload: (c: Connection, form: FormData) => request<ManagedDocument>("/api/v2/documents", { method: "POST", body: form }, c),
  withdraw: (c: Connection, id: string) => request<{ status: string }>(`/api/v2/documents/${encodeURIComponent(id)}`, { method: "DELETE" }, c),
  publish: (c: Connection) => request<{ job_id: string }>("/api/v2/index/publish", { method: "POST" }, c),
  job: (c: Connection, id: string) => request<Job>(`/api/v2/jobs/${encodeURIComponent(id)}`, {}, c),
  retry: (c: Connection, id: string) => request<{ job_id: string }>(`/api/v2/jobs/${encodeURIComponent(id)}/retry`, { method: "POST" }, c),
  releases: (c: Connection) => request<{ active: string | null; releases: Release[] }>("/api/v2/index/releases", {}, c),
  rollback: (c: Connection, id: string) => request<{ active: string }>(`/api/v2/index/rollback/${encodeURIComponent(id)}`, { method: "POST" }, c),
  async original(c: Connection, path: string) {
    const response = await fetch(path, { headers: authHeaders(c) });
    if (!response.ok) throw new ApiError(STATUS_HINTS[response.status] || "无法打开原文", response.status);
    return URL.createObjectURL(await response.blob());
  },
};
