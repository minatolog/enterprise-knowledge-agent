import {
  BookOpen,
  ChevronLeft,
  ChevronRight,
  History,
  MessageSquare,
  Network,
  PanelLeftClose,
  Plus,
  Search,
  Settings2,
  X,
} from "lucide-react";
import type { Conversation } from "../state/conversations";
import { dateGroup } from "../state/conversations";
export type Page = "chat" | "knowledge" | "workflow" | "runs" | "settings";
interface Props {
  page: Page;
  onNavigate: (page: Page) => void;
  blocked?: boolean;
  mobile: boolean;
  collapsed: boolean;
  onCollapse: () => void;
  drawer: boolean;
  onClose: () => void;
  conversations: Conversation[];
  activeId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
  search: string;
  onSearch: (value: string) => void;
  saved: boolean;
}
export function ProductLogo() {
  return (
    <span className="product-logo">
      <Network size={21} strokeWidth={1.6} />
    </span>
  );
}
export default function Sidebar(p: Props) {
  const filtered = p.conversations
    .filter(
      (c) =>
        c.turns.length &&
        `${c.title} ${c.turns.map((t) => t.question).join(" ")}`
          .toLowerCase()
          .includes(p.search.toLowerCase()),
    )
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  const groups = [...new Set(filtered.map((c) => dateGroup(c.updatedAt)))];
  const navigate = (page: Page) => {
    p.onNavigate(page);
    p.onClose();
  };
  return (
    <>
      <button
        className={`drawer-backdrop ${p.drawer ? "visible" : ""}`}
        aria-label="关闭导航遮罩"
        onClick={p.onClose}
        tabIndex={p.drawer ? 0 : -1}
      />
      <aside
        className={`assistant-sidebar ${p.collapsed ? "collapsed" : ""} ${p.drawer ? "drawer-open" : ""}`}
        aria-label="主导航"
        inert={p.blocked || (p.mobile && !p.drawer) ? true : undefined}
      >
        <div className="sidebar-brand">
          <ProductLogo />
          <div className="sidebar-brand-copy">
            <strong>CNOOC</strong>
            <span>Enterprise Knowledge Assistant</span>
          </div>
          <button
            className="mobile-only icon-btn"
            onClick={p.onClose}
            aria-label="关闭导航"
          >
            <X size={17} />
          </button>
          <button
            className="desktop-only icon-btn collapse-button"
            onClick={p.onCollapse}
            aria-label={p.collapsed ? "展开侧栏" : "折叠侧栏"}
          >
            {p.collapsed ? (
              <ChevronRight size={16} />
            ) : (
              <PanelLeftClose size={16} />
            )}
          </button>
        </div>
        <button
          className="new-chat-button"
          onClick={() => {
            p.onNew();
            navigate("chat");
          }}
          title="新建对话"
        >
          <Plus size={17} />
          <span>新建对话</span>
          <kbd>＋</kbd>
        </button>
        <div className="sidebar-search">
          <Search size={15} />
          <input
            aria-label="搜索对话"
            placeholder="搜索对话"
            value={p.search}
            onChange={(e) => p.onSearch(e.target.value)}
          />
        </div>
        <nav>
          {(
            [
              { id: "chat", label: "知识问答", icon: MessageSquare },
              { id: "knowledge", label: "知识库", icon: BookOpen },
              { id: "workflow", label: "工作流", icon: Network },
              { id: "runs", label: "运行记录", icon: History },
            ] as const
          ).map((item) => (
            <button
              key={item.id}
              title={item.label}
              aria-current={p.page === item.id ? "page" : undefined}
              className={
                p.page === item.id ? "sidebar-nav active" : "sidebar-nav"
              }
              onClick={() => navigate(item.id)}
            >
              <item.icon size={17} />
              <span>{item.label}</span>
              {p.page === item.id && <i />}
            </button>
          ))}
        </nav>
        <div className="conversation-history">
          <div className="history-caption">
            最近对话 <span>{p.saved ? "此浏览器" : "本次打开"}</span>
          </div>
          {!filtered.length ? (
            <p className="history-empty">
              {p.search ? "未找到匹配的对话" : "开始提问后，对话会出现在这里。"}
            </p>
          ) : (
            groups.map((group) => (
              <section key={group}>
                <h3>{group}</h3>
                {filtered
                  .filter((c) => dateGroup(c.updatedAt) === group)
                  .map((c) => (
                    <button
                      key={c.id}
                      className={`history-item ${p.activeId === c.id && p.page === "chat" ? "selected" : ""}`}
                      title={c.title}
                      onClick={() => {
                        p.onSelect(c.id);
                        navigate("chat");
                      }}
                    >
                      <MessageSquare size={13} />
                      <span>{c.title}</span>
                    </button>
                  ))}
              </section>
            ))
          )}
        </div>
        <div className="sidebar-bottom">
          <button
            title="设置"
            className={`sidebar-nav ${p.page === "settings" ? "active" : ""}`}
            onClick={() => navigate("settings")}
          >
            <Settings2 size={17} />
            <span>设置与偏好</span>
          </button>
          <div className="sidebar-environment">
            <span className="environment-avatar">L</span>
            <div>
              本地工作空间
              <small>
                {p.saved ? "历史保存于此浏览器" : "对话仅保留在本次打开期间"}
              </small>
            </div>
            <ChevronLeft size={12} />
          </div>
        </div>
      </aside>
    </>
  );
}
