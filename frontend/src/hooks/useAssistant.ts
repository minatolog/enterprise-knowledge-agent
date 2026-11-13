import { useCallback, useEffect, useRef, useState } from "react";
import { api, type DocumentList } from "../api";
import {
  createConversation,
  parseHistory,
  serializeHistory,
  HISTORY_KEY,
  HISTORY_OPT_IN,
  type Conversation,
  type Turn,
} from "../state/conversations";
function initialState() {
  try {
    const save = localStorage.getItem(HISTORY_OPT_IN) === "true";
    const conversations = save
      ? parseHistory(localStorage.getItem(HISTORY_KEY))
      : [];
    return {
      save,
      conversations: conversations.length
        ? conversations
        : [createConversation()],
    };
  } catch {
    return { save: false, conversations: [createConversation()] };
  }
}
export function useAssistant() {
  const [initial] = useState(initialState);
  const [conversations, setConversations] = useState(initial.conversations);
  const [activeId, setActiveId] = useState(initial.conversations[0].id);
  const [saveHistory, setSaveHistory] = useState(initial.save);
  const [historyError, setHistoryError] = useState("");
  const [documents, setDocuments] = useState<DocumentList | null>(null);
  const [documentsError, setDocumentsError] = useState("");
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [health, setHealth] = useState<"loading" | "online" | "offline">(
    "loading",
  );
  const [topK, setTopK] = useState(3);
  const [pending, setPending] = useState<{
    conversationId: string;
    question: string;
    replacing?: string;
  } | null>(null);
  const [runs, setRuns] = useState<Turn[]>([]);
  const inFlight = useRef(false),
    abort = useRef<AbortController | null>(null);
  const active =
    conversations.find((c) => c.id === activeId) || conversations[0];
  const loadDocuments = useCallback(async () => {
    setDocumentsLoading(true);
    setDocumentsError("");
    try {
      setDocuments(await api.documents());
    } catch (e) {
      setDocumentsError((e as Error).message);
    } finally {
      setDocumentsLoading(false);
    }
  }, []);
  useEffect(() => {
    void api
      .health()
      .then((d) => setHealth(d.status === "ok" ? "online" : "offline"))
      .catch(() => setHealth("offline"));
    void loadDocuments();
    return () => abort.current?.abort();
  }, [loadDocuments]);
  useEffect(() => {
    try {
      localStorage.setItem(HISTORY_OPT_IN, String(saveHistory));
      if (saveHistory)
        localStorage.setItem(HISTORY_KEY, serializeHistory(conversations));
      else localStorage.removeItem(HISTORY_KEY);
      setHistoryError("");
    } catch {
      setHistoryError("浏览器存储不可用或空间不足；本次对话仍在页面内存中。");
    }
  }, [saveHistory, conversations]);
  function newChat() {
    const empty = conversations.find(
      (c) => !c.turns.length && c.id !== pending?.conversationId,
    );
    if (empty) {
      setActiveId(empty.id);
      return;
    }
    const conversation = createConversation();
    setConversations((prev) => [conversation, ...prev]);
    setActiveId(conversation.id);
  }
  async function send(question: string, replaceTurnId?: string) {
    const value = question.trim();
    if (!value || value.length > 2000 || inFlight.current) return;
    inFlight.current = true;
    const conversationId = active.id,
      submittedTopK = topK;
    setPending({ conversationId, question: value, replacing: replaceTurnId });
    const controller = new AbortController();
    abort.current = controller;
    const timer = setTimeout(() => controller.abort(), 180000);
    const turn: Turn = {
      id: crypto.randomUUID(),
      question: value,
      createdAt: new Date().toISOString(),
      topK: submittedTopK,
    };
    try {
      turn.result = await api.query(value, submittedTopK, controller.signal);
    } catch (e) {
      turn.error =
        (e as Error).name === "AbortError"
          ? "等待超过 180 秒，浏览器已停止等待；后端可能仍在执行。可稍后重新请求。"
          : (e as Error).message;
    } finally {
      clearTimeout(timer);
      abort.current = null;
    }
    setConversations((prev) =>
      prev.map((c) =>
        c.id !== conversationId
          ? c
          : {
              ...c,
              title: c.turns.length ? c.title : value.slice(0, 80),
              updatedAt: turn.createdAt,
              turns: replaceTurnId
                ? c.turns.map((t) => (t.id === replaceTurnId ? turn : t))
                : [...c.turns, turn],
            },
      ),
    );
    setRuns((prev) => [turn, ...prev]);
    setPending(null);
    inFlight.current = false;
  }
  return {
    active,
    activeId,
    conversations,
    selectConversation: setActiveId,
    newChat,
    send,
    pending,
    runs,
    documents,
    documentsError,
    documentsLoading,
    loadDocuments,
    health,
    topK,
    setTopK,
    saveHistory,
    setSaveHistory,
    historyError,
  };
}
