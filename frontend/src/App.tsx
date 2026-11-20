import { useEffect, useState } from "react";
import { Menu } from "lucide-react";
import Nav, { PAGE_NAMES, type Page } from "./components/Nav";
import Ask, { type Focus } from "./components/Ask";
import EvidencePanel from "./components/EvidencePanel";
import Library from "./components/Library";
import Evaluation from "./components/Evaluation";
import Manage from "./components/Manage";
import Settings from "./components/Settings";
import { useAssistant } from "./state/useAssistant";

function pageFromHash(): Page {
  const value = location.hash.slice(1);
  return (Object.keys(PAGE_NAMES) as Page[]).includes(value as Page) ? (value as Page) : "ask";
}

export default function App() {
  const assistant = useAssistant();
  const [page, setPage] = useState<Page>(pageFromHash);
  const [navOpen, setNavOpen] = useState(false);
  const [focus, setFocus] = useState<Focus | null>(null);

  useEffect(() => {
    const onHash = () => setPage(pageFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setFocus(null);
      setNavOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => setFocus(null), [assistant.activeId]);

  useEffect(() => {
    document.title = `${PAGE_NAMES[page]}｜制度知识助手`;
  }, [page]);

  const navigate = (next: Page) => {
    location.hash = next;
    setPage(next);
    setNavOpen(false);
  };

  const focusedTurn = focus && page === "ask" ? assistant.active.turns.find((t) => t.id === focus.turnId) : undefined;

  return (
    <div className={`app${focusedTurn?.result ? " has-evidence" : ""}`}>
      <Nav page={page} onNavigate={navigate} assistant={assistant} open={navOpen} onClose={() => setNavOpen(false)} />
      {navOpen && <button className="scrim" aria-label="关闭导航" onClick={() => setNavOpen(false)} />}
      <main className="main">
        <header className="topbar">
          <button className="icon-button" onClick={() => setNavOpen(true)} aria-label="打开导航">
            <Menu size={20} />
          </button>
          <span>{PAGE_NAMES[page]}</span>
        </header>
        {page === "ask" && <Ask assistant={assistant} focus={focus} onFocus={setFocus} />}
        {page === "library" && <Library assistant={assistant} />}
        {page === "evaluation" && <Evaluation />}
        {page === "manage" && <Manage assistant={assistant} />}
        {page === "settings" && <Settings assistant={assistant} />}
      </main>
      {focusedTurn?.result && (
        <EvidencePanel
          result={focusedTurn.result}
          index={focus!.index}
          onSelect={(index) => setFocus({ turnId: focusedTurn.id, index })}
          onClose={() => setFocus(null)}
          connection={assistant.connection}
        />
      )}
    </div>
  );
}
