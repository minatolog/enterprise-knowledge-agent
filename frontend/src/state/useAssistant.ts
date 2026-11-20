import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, type Connection, type DocumentList, type ServiceConfig } from "../api";
import { historyFrom } from "../utils/evidence";
import { newId } from "../utils/id";
import {
  createConversation,
  HISTORY_KEY,
  parseHistory,
  serializeHistory,
  type Conversation,
  type Turn,
} from "./conversations";
import {
  loadPreferences,
  loadToken,
  savePreferences,
  saveToken,
  type Preferences,
} from "./preferences";

export type Health = "checking" | "online" | "offline";

function initialConversations(save: boolean): Conversation[] {
  if (!save) return [];
  try {
    return parseHistory(localStorage.getItem(HISTORY_KEY));
  } catch {
    return [];
  }
}

export function useAssistant() {
  const [prefs, setPrefsState] = useState<Preferences>(loadPreferences);
  const [token, setTokenState] = useState(loadToken);
  const connection: Connection = useMemo(() => ({ mode: prefs.mode, token }), [prefs.mode, token]);

  const [conversations, setConversations] = useState<Conversation[]>(() => {
    const restored = initialConversations(loadPreferences().saveHistory);
    return restored.length ? restored : [createConversation(loadPreferences().mode)];
  });
  const [activeId, setActiveId] = useState(() => conversations[0].id);
  const [pending, setPending] = useState<{ conversationId: string; question: string } | null>(null);
  const [storageError, setStorageError] = useState("");
  const [health, setHealth] = useState<Health>("checking");
  const [documents, setDocuments] = useState<DocumentList | null>(null);
  const [config, setConfig] = useState<ServiceConfig | null>(null);
  const abort = useRef<AbortController | null>(null);

  const active = conversations.find((c) => c.id === activeId) || conversations[0];

  const setPrefs = useCallback((patch: Partial<Preferences>) => {
    setPrefsState((current) => {
      const next = { ...current, ...patch };
      savePreferences(next);
      return next;
    });
  }, []);

  const setToken = useCallback(
    (value: string) => {
      setTokenState(value);
      saveToken(value, prefs.rememberToken);
    },
    [prefs.rememberToken],
  );

  const refreshLocal = useCallback(async () => {
    try {
      await api.health();
      setHealth("online");
    } catch {
      setHealth("offline");
      return;
    }
    const [docs, cfg] = await Promise.allSettled([api.documents(), api.config()]);
    setDocuments(docs.status === "fulfilled" ? docs.value : null);
    setConfig(cfg.status === "fulfilled" ? cfg.value : null);
  }, []);

  useEffect(() => {
    void refreshLocal();
    return () => abort.current?.abort();
  }, [refreshLocal]);

  useEffect(() => {
    try {
      if (prefs.saveHistory) localStorage.setItem(HISTORY_KEY, serializeHistory(conversations));
      else localStorage.removeItem(HISTORY_KEY);
      setStorageError("");
    } catch {
      setStorageError("浏览器存储已满或不可用，对话只保留在当前页面。");
    }
  }, [prefs.saveHistory, conversations]);

  const update = (id: string, change: (c: Conversation) => Conversation) =>
    setConversations((list) => list.map((c) => (c.id === id ? change(c) : c)));

  const send = useCallback(
    async (question: string, replaceTurnId?: string) => {
      const text = question.trim();
      if (!text || pending) return;
      let conversation = active;
      // A conversation belongs to one knowledge service; switching mode starts a new one.
      if ((conversation.mode || "local") !== prefs.mode && conversation.turns.length) {
        conversation = createConversation(prefs.mode);
        setConversations((list) => [conversation, ...list]);
        setActiveId(conversation.id);
      }
      const id = conversation.id;
      const earlier = replaceTurnId
        ? conversation.turns.slice(0, conversation.turns.findIndex((t) => t.id === replaceTurnId))
        : conversation.turns;
      const controller = new AbortController();
      abort.current = controller;
      setPending({ conversationId: id, question: text });
      const turn: Turn = { id: newId(), question: text, createdAt: new Date().toISOString(), topK: prefs.topK };
      try {
        turn.result = await api.query(
          connection,
          { question: text, topK: prefs.topK, history: historyFrom(earlier), sessionId: id },
          controller.signal,
        );
      } catch (error) {
        if ((error as Error).name === "AbortError") {
          setPending(null);
          return;
        }
        turn.error = (error as Error).message;
      }
      setPending(null);
      update(id, (c) => {
        const turns = replaceTurnId ? c.turns.map((t) => (t.id === replaceTurnId ? turn : t)) : [...c.turns, turn];
        return {
          ...c,
          mode: prefs.mode,
          title: c.turns.length ? c.title : text.slice(0, 40),
          updatedAt: turn.createdAt,
          turns,
        };
      });
    },
    [active, connection, pending, prefs.mode, prefs.topK],
  );

  const stop = useCallback(() => abort.current?.abort(), []);

  const newConversation = useCallback(() => {
    if (!active.turns.length && (active.mode || "local") === prefs.mode) return;
    const fresh = createConversation(prefs.mode);
    setConversations((list) => [fresh, ...list.filter((c) => c.turns.length)]);
    setActiveId(fresh.id);
  }, [active, prefs.mode]);

  const removeConversation = useCallback(
    (id: string) => {
      setConversations((list) => {
        const rest = list.filter((c) => c.id !== id);
        const next = rest.length ? rest : [createConversation(prefs.mode)];
        if (id === activeId) setActiveId(next[0].id);
        return next;
      });
    },
    [activeId, prefs.mode],
  );

  const clearHistory = useCallback(() => {
    const fresh = createConversation(prefs.mode);
    setConversations([fresh]);
    setActiveId(fresh.id);
  }, [prefs.mode]);

  return {
    prefs,
    setPrefs,
    token,
    setToken,
    connection,
    conversations,
    active,
    activeId,
    select: setActiveId,
    newConversation,
    removeConversation,
    clearHistory,
    send,
    stop,
    pending,
    storageError,
    health,
    documents,
    config,
    refreshLocal,
  };
}

export type Assistant = ReturnType<typeof useAssistant>;
