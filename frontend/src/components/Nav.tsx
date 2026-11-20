import { BookOpen, FolderCog, Gauge, MessageSquareText, Plus, Settings, Trash2, X } from "lucide-react";
import type { Assistant } from "../state/useAssistant";
import { dateGroup } from "../state/conversations";
import Mark from "./Mark";

export type Page = "ask" | "library" | "evaluation" | "manage" | "settings";

export const PAGE_NAMES: Record<Page, string> = {
  ask: "问答",
  library: "知识库",
  evaluation: "检索评测",
  manage: "资料管理",
  settings: "设置",
};

const ICONS = { ask: MessageSquareText, library: BookOpen, evaluation: Gauge, manage: FolderCog, settings: Settings };

export default function Nav({
  page,
  onNavigate,
  assistant,
  open,
  onClose,
}: {
  page: Page;
  onNavigate: (page: Page) => void;
  assistant: Assistant;
  open: boolean;
  onClose: () => void;
}) {
  const pages: Page[] = assistant.prefs.mode === "enterprise"
    ? ["ask", "library", "evaluation", "manage", "settings"]
    : ["ask", "library", "evaluation", "settings"];
  const history = assistant.conversations.filter((c) => c.turns.length);
  let lastGroup = "";
  return (
    <nav className={`nav${open ? " is-open" : ""}`} aria-label="主导航">
      <div className="nav-brand">
        <Mark />
        <div>
          <strong>制度知识助手</strong>
          <span>{assistant.prefs.mode === "enterprise" ? "企业知识库" : "中国海洋石油有限公司公开资料"}</span>
        </div>
        <button className="icon-button nav-close" onClick={onClose} aria-label="关闭导航">
          <X size={18} />
        </button>
      </div>

      <ul className="nav-pages">
        {pages.map((item) => {
          const Icon = ICONS[item];
          return (
            <li key={item}>
              <button className={page === item ? "is-current" : ""} aria-current={page === item ? "page" : undefined} onClick={() => onNavigate(item)}>
                <Icon size={17} strokeWidth={1.7} aria-hidden="true" />
                {PAGE_NAMES[item]}
              </button>
            </li>
          );
        })}
      </ul>

      <div className="nav-history">
        <button
          className="new-chat"
          onClick={() => {
            assistant.newConversation();
            onNavigate("ask");
          }}
        >
          <Plus size={16} aria-hidden="true" /> 新的提问
        </button>
        {history.length === 0 ? (
          <p className="nav-empty">提过的问题会出现在这里。</p>
        ) : (
          <ol>
            {history.map((c) => {
              const group = dateGroup(c.updatedAt);
              const heading = group !== lastGroup ? group : "";
              lastGroup = group;
              return (
                <li key={c.id}>
                  {heading && <h3>{heading}</h3>}
                  <div className={`history-item${c.id === assistant.activeId ? " is-current" : ""}`}>
                    <button
                      className="history-open"
                      onClick={() => {
                        assistant.select(c.id);
                        onNavigate("ask");
                      }}
                      title={c.title}
                    >
                      {c.title}
                      {c.mode === "enterprise" && <span className="history-mode">企业</span>}
                    </button>
                    <button className="icon-button history-remove" aria-label={`删除对话：${c.title}`} onClick={() => assistant.removeConversation(c.id)}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </div>

      <footer className="nav-status">
        <span className={`dot ${assistant.prefs.mode === "enterprise" ? (assistant.token ? "online" : "offline") : assistant.health}`} aria-hidden="true" />
        {assistant.prefs.mode === "enterprise"
          ? assistant.token ? "企业知识库" : "企业知识库：未设置令牌"
          : assistant.health === "online" ? "本地知识库已连接" : assistant.health === "checking" ? "正在连接本地服务" : "本地服务未连接"}
        {!assistant.prefs.saveHistory && <small>对话不会保存到浏览器</small>}
      </footer>
    </nav>
  );
}
