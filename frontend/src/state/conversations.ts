import type { Answer } from "../api";
export interface Turn {
  id: string;
  question: string;
  createdAt: string;
  topK: number;
  result?: Answer;
  error?: string;
}
export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  turns: Turn[];
}
export const HISTORY_KEY = "cnooc-assistant-history-v1";
export const HISTORY_OPT_IN = "cnooc-assistant-save-history";
export function createConversation(): Conversation {
  const now = new Date().toISOString();
  return {
    id: crypto.randomUUID(),
    title: "新对话",
    createdAt: now,
    updatedAt: now,
    turns: [],
  };
}
const object = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);
const text = (value: unknown, max = 100000): value is string =>
  typeof value === "string" && value.length <= max;
const finite = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value);
const date = (value: unknown): value is string =>
  text(value, 40) && Number.isFinite(Date.parse(value));
function validAnswer(value: unknown): value is Answer {
  if (
    !object(value) ||
    !text(value.answer) ||
    !text(value.request_id, 256) ||
    !finite(value.retrieval_count) ||
    !object(value.timings_ms) ||
    !Object.values(value.timings_ms).every(finite) ||
    !Array.isArray(value.sources) ||
    value.sources.length > 100
  )
    return false;
  return value.sources.every(
    (s) =>
      object(s) &&
      text(s.chunk_id, 1024) &&
      text(s.source, 4096) &&
      text(s.relative_path, 4096) &&
      finite(s.page_start) &&
      finite(s.page_end) &&
      text(s.label, 4096) &&
      (s.source_url === null || text(s.source_url, 8192)) &&
      (s.rerank_score === null || finite(s.rerank_score)),
  );
}
export function parseHistory(raw: string | null): Conversation[] {
  if (!raw || raw.length > 5_000_000) return [];
  try {
    const data: unknown = JSON.parse(raw);
    if (
      !object(data) ||
      data.version !== 1 ||
      !Array.isArray(data.conversations) ||
      data.conversations.length > 50
    )
      return [];
    const ids = new Set<string>();
    return data.conversations.filter((c): c is Conversation => {
      if (
        !object(c) ||
        !text(c.id, 128) ||
        !c.id ||
        ids.has(c.id) ||
        !text(c.title, 2000) ||
        !date(c.createdAt) ||
        !date(c.updatedAt) ||
        !Array.isArray(c.turns) ||
        c.turns.length > 100
      )
        return false;
      const turnIds = new Set<string>();
      const valid = c.turns.every((t) => {
        if (
          !object(t) ||
          !text(t.id, 128) ||
          turnIds.has(t.id) ||
          !text(t.question, 2000) ||
          !date(t.createdAt) ||
          !finite(t.topK) ||
          ![3, 5, 8].includes(t.topK) ||
          (!validAnswer(t.result) && !text(t.error, 10000))
        )
          return false;
        if (t.result !== undefined && !validAnswer(t.result)) return false;
        turnIds.add(t.id);
        return true;
      });
      if (valid) ids.add(c.id);
      return valid;
    });
  } catch {
    return [];
  }
}
export function serializeHistory(conversations: Conversation[]): string {
  return JSON.stringify({
    version: 1,
    conversations: conversations
      .filter((c) => c.turns.length)
      .slice(0, 50)
      .map((c) => ({ ...c, turns: c.turns.slice(-100) })),
  });
}
export function dateGroup(iso: string, now = new Date()): string {
  const d = new Date(iso),
    midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (d >= midnight) return "今天";
  const yesterday = new Date(midnight);
  yesterday.setDate(yesterday.getDate() - 1);
  if (d >= yesterday) return "昨天";
  return d.toLocaleDateString("zh-CN", { month: "long", day: "numeric" });
}
