import { useEffect, useState } from "react";
import {
  Check,
  Menu,
  MessageSquare,
  PanelLeftOpen,
  ShieldCheck,
  X,
} from "lucide-react";
import Sidebar, { type Page } from "./components/Sidebar";
import Chat from "./components/Chat";
import {
  KnowledgeBasePage,
  RunsPage,
  SettingsPage,
  WorkflowPage,
} from "./components/Pages";
import { SourceDetailPanel } from "./components/SourceDetails";
import { useAssistant } from "./hooks/useAssistant";
import type { Source } from "./api";
const pageNames: Record<Page, string> = {
  chat: "知识问答",
  knowledge: "知识库",
  workflow: "工作流",
  runs: "运行记录",
  settings: "设置",
};
function currentPage(): Page {
  const value = location.hash.slice(1);
  return Object.hasOwn(pageNames, value) ? (value as Page) : "chat";
}
function useMedia(query: string) {
  const [value, setValue] = useState(() => matchMedia(query).matches);
  useEffect(() => {
    const media = matchMedia(query),
      listener = () => setValue(media.matches);
    media.addEventListener("change", listener);
    return () => media.removeEventListener("change", listener);
  }, [query]);
  return value;
}
export default function App() {
  const assistant = useAssistant();
  const [page, setPage] = useState<Page>(currentPage),
    [collapsed, setCollapsed] = useState(false),
    [drawer, setDrawer] = useState(false),
    [historySearch, setHistorySearch] = useState(""),
    [draft, setDraft] = useState(""),
    [source, setSource] = useState<Source | null>(null),
    [notice, setNotice] = useState("");
  const [motion, setMotion] = useState(() => {
    try {
      return localStorage.getItem("studio-motion") !== "off";
    } catch {
      return true;
    }
  });
  const reduced = useMedia("(prefers-reduced-motion: reduce)"),
    mobile = useMedia("(max-width: 760px)");
  const animated = motion && !reduced;
  useEffect(() => {
    const listener = () => {
      setPage(currentPage());
      setSource(null);
    };
    window.addEventListener("hashchange", listener);
    return () => window.removeEventListener("hashchange", listener);
  }, []);
  useEffect(() => {
    try {
      localStorage.setItem("studio-motion", motion ? "on" : "off");
    } catch {
      /* Preference remains in memory. */
    }
  }, [motion]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 3500);
    return () => clearTimeout(timer);
  }, [notice]);
  useEffect(() => {
    const escape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setDrawer(false);
        setSource(null);
      }
    };
    window.addEventListener("keydown", escape);
    return () => window.removeEventListener("keydown", escape);
  }, []);
  useEffect(() => {
    if (!drawer) return;
    const previous = document.activeElement as HTMLElement | null;
    document.querySelector<HTMLInputElement>(".sidebar-search input")?.focus();
    return () => previous?.focus();
  }, [drawer]);
  useEffect(() => {
    if (!source) return;
    const previous = document.activeElement as HTMLElement | null;
    document
      .querySelector<HTMLButtonElement>(".source-detail-panel .icon-btn")
      ?.focus();
    return () => previous?.focus();
  }, [source]);
  const navigate = (next: Page) => {
    location.hash = next;
    setPage(next);
    setDrawer(false);
    setSource(null);
  };
  const send = () => {
    if (!draft.trim() || assistant.pending) return;
    const question = draft;
    setDraft("");
    void assistant.send(question);
  };
  const chooseConversation = (id: string) => {
    assistant.selectConversation(id);
    setDraft("");
    setSource(null);
  };
  return (
    <div className="assistant-shell" data-motion={animated ? "on" : "off"}>
      <Sidebar
        page={page}
        onNavigate={navigate}
        collapsed={collapsed}
        onCollapse={() => setCollapsed(!collapsed)}
        drawer={drawer}
        blocked={Boolean(source)}
        onClose={() => setDrawer(false)}
        mobile={mobile}
        conversations={assistant.conversations}
        activeId={assistant.activeId}
        onSelect={chooseConversation}
        onNew={() => {
          assistant.newChat();
          setDraft("");
        }}
        search={historySearch}
        onSearch={setHistorySearch}
        saved={assistant.saveHistory}
      />
      <div
        className="assistant-main"
        inert={source || (drawer && mobile) ? true : undefined}
      >
        <header className="chat-header">
          <div className="header-product">
            <button
              className="mobile-only icon-btn"
              aria-label="打开导航"
              onClick={() => setDrawer(true)}
            >
              <Menu size={19} />
            </button>
            {collapsed && (
              <button
                className="desktop-only icon-btn"
                aria-label="展开导航"
                onClick={() => setCollapsed(false)}
              >
                <PanelLeftOpen size={17} />
              </button>
            )}
            <span>
              CNOOC <strong>Enterprise Knowledge Assistant</strong>
            </span>
            <i />
            <span className="current-page">{pageNames[page]}</span>
          </div>
          <div className="header-status">
            <span className={`api-indicator ${assistant.health}`} />
            {assistant.health === "online"
              ? "本地 API 已连接"
              : assistant.health === "loading"
                ? "正在连接"
                : "API 未连接"}
            <span className="local-label">本地原型</span>
          </div>
        </header>
        <main key={page} className={`assistant-content content-${page}`}>
          {page === "chat" && (
            <Chat
              conversation={assistant.active}
              draft={draft}
              onDraft={setDraft}
              onSend={send}
              onRegenerate={(turn) =>
                void assistant.send(turn.question, turn.id)
              }
              pending={assistant.pending}
              onSource={setSource}
              topK={assistant.topK}
              onTopK={assistant.setTopK}
            />
          )}
          {page === "knowledge" && (
            <KnowledgeBasePage
              data={assistant.documents}
              loading={assistant.documentsLoading}
              error={assistant.documentsError}
              onRefresh={() => void assistant.loadDocuments()}
            />
          )}
          {page === "workflow" && (
            <WorkflowPage
              animated={animated}
              pending={Boolean(assistant.pending)}
              draft={draft}
              onDraft={setDraft}
              onSend={send}
              topK={assistant.topK}
              onTopK={assistant.setTopK}
              onNotice={setNotice}
              last={assistant.runs[0]}
            />
          )}
          {page === "runs" && (
            <RunsPage runs={assistant.runs} onSource={setSource} />
          )}
          {page === "settings" && (
            <SettingsPage
              topK={assistant.topK}
              onTopK={assistant.setTopK}
              save={assistant.saveHistory}
              onSave={assistant.setSaveHistory}
              storageError={assistant.historyError}
              motion={motion}
              onMotion={setMotion}
              reduced={reduced}
            />
          )}
        </main>
        <div className="application-footnote">
          <ShieldCheck size={11} />
          <span>CNOOC 官方资料</span>
          <span>·</span>
          <span>
            {assistant.saveHistory
              ? "历史保存在此浏览器"
              : "历史仅本次打开可用"}
          </span>
          {assistant.pending && (
            <span className="global-pending">请求执行中</span>
          )}
        </div>
      </div>
      {source && (
        <>
          <button
            className="source-backdrop"
            aria-label="关闭来源详情遮罩"
            onClick={() => setSource(null)}
          />
          <SourceDetailPanel source={source} onClose={() => setSource(null)} />
        </>
      )}
      {notice && (
        <div className="assistant-toast" role="status">
          <Check size={15} />
          {notice}
          <button
            className="icon-btn"
            onClick={() => setNotice("")}
            aria-label="关闭提示"
          >
            <X size={13} />
          </button>
        </div>
      )}
    </div>
  );
}
