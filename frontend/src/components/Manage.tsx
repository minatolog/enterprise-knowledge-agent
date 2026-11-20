import { useCallback, useEffect, useRef, useState } from "react";
import { RotateCcw, Upload } from "lucide-react";
import { api, type Job, type ManagedDocument, type Me, type Release } from "../api";
import type { Assistant } from "../state/useAssistant";
import { StatusTag } from "./Library";

const when = (seconds: number) => new Date(seconds * 1000).toLocaleString("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });

export default function Manage({ assistant }: { assistant: Assistant }) {
  const c = assistant.connection;
  const [me, setMe] = useState<Me | null>(null);
  const [docs, setDocs] = useState<ManagedDocument[]>([]);
  const [releases, setReleases] = useState<{ active: string | null; releases: Release[] } | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const form = useRef<HTMLFormElement>(null);
  const isAdmin = me?.roles.includes("admin");
  const canEdit = isAdmin || me?.roles.includes("editor");

  const load = useCallback(async () => {
    setError("");
    try {
      const who = await api.me(c);
      setMe(who);
      setDocs(await api.managedDocuments(c));
      setReleases(who.roles.includes("admin") ? await api.releases(c) : null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [c]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!job || job.status === "succeeded" || job.status === "failed") return;
    const timer = setTimeout(async () => {
      try {
        const next = await api.job(c, job.id);
        setJob(next);
        if (next.status === "succeeded" || next.status === "failed") void load();
      } catch (e) {
        setError((e as Error).message);
      }
    }, 1500);
    return () => clearTimeout(timer);
  }, [job, c, load]);

  const act = async (action: () => Promise<unknown>, done: string) => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await action();
      setMessage(done);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (!assistant.token)
    return (
      <div className="page">
        <header className="page-head"><h1>资料管理</h1></header>
        <div className="notice notice-warn"><p>先在“设置”里填入企业令牌。开发环境可用 <code>python scripts/enterprise.py token --tenant demo --groups staff --roles admin</code> 生成。</p></div>
      </div>
    );

  const pendingCount = docs.filter((d) => d.status !== "published").length;
  const latest = releases?.releases.find((r) => r.id === releases.active);

  return (
    <div className="page">
      <header className="page-head">
        <h1>资料管理</h1>
        {me && <span className="whoami">{me.subject}，租户 {me.tenant}，用户组 {me.groups.join("、") || "无"}</span>}
      </header>
      {error && <div className="notice notice-error" role="alert"><p>{error}</p></div>}
      {message && <div className="notice notice-ok" role="status"><p>{message}</p></div>}

      {canEdit && (
        <section className="settings-block">
          <h2>上传资料</h2>
          <form
            ref={form}
            className="upload"
            onSubmit={(event) => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              const groups = String(data.get("groups_text") || "").split(/[,，\s]+/).filter(Boolean);
              data.delete("groups_text");
              data.set("groups", JSON.stringify(groups));
              void act(async () => {
                await api.upload(c, data);
                form.current?.reset();
              }, "已上传。发布新版本后，问答才会用到它。");
            }}
          >
            <label>标题<input name="title" required maxLength={512} placeholder="例如：差旅费管理办法（2026 版）" /></label>
            <label>可见用户组<input name="groups_text" required placeholder="用逗号分隔，例如 staff, finance" /></label>
            <label>文件<input name="file" type="file" required accept=".pdf,.docx,.md,.txt" /></label>
            <button className="primary" disabled={busy}><Upload size={15} /> 上传</button>
          </form>
        </section>
      )}

      <section className="settings-block">
        <div className="block-head">
          <h2>资料与发布</h2>
          {canEdit && (
            <button className="primary" disabled={busy || job?.status === "running" || job?.status === "queued"} onClick={() => void act(async () => {
              const { job_id } = await api.publish(c);
              setJob({ id: job_id, status: "queued", attempts: 0, error: null, release_id: null });
            }, "")}>
              发布新版本{pendingCount ? `（${pendingCount} 份待处理）` : ""}
            </button>
          )}
        </div>
        {job && (
          <p className={`job job-${job.status}`}>
            {{ queued: "发布任务排队中…", running: "正在解析和建立索引…", succeeded: "发布完成。", failed: `发布失败：${job.error || "未知错误"}` }[job.status]}
            {job.status === "failed" && (
              <button className="text-button" onClick={() => void act(async () => setJob({ ...job, status: "queued", id: (await api.retry(c, job.id)).job_id }), "已重新提交发布任务。")}>
                <RotateCcw size={14} /> 重试
              </button>
            )}
          </p>
        )}
        {docs.length === 0 ? (
          <p className="lead">还没有资料。上传第一份文件后点“发布新版本”。</p>
        ) : (
          <table className="table">
            <thead><tr><th scope="col">资料</th><th scope="col">可见用户组</th><th scope="col">状态</th>{isAdmin && <th scope="col"><span className="visually-hidden">操作</span></th>}</tr></thead>
            <tbody>
              {docs.map((doc) => (
                <tr key={doc.id}>
                  <td><span className="doc-title">{doc.title}</span><span className="doc-path">第 {doc.version} 版{doc.published_version && doc.published_version !== doc.version ? `，线上为第 ${doc.published_version} 版` : ""}</span></td>
                  <td>{doc.groups.join("、")}</td>
                  <td><StatusTag status={doc.status} /></td>
                  {isAdmin && (
                    <td className="row-actions">
                      <button className="text-button danger" disabled={busy} onClick={() => {
                        if (window.confirm(`撤回“${doc.title}”？撤回后立即从问答中排除，版本记录会保留。`))
                          void act(() => api.withdraw(c, doc.id), `已撤回“${doc.title}”。`);
                      }}>撤回</button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {latest && latest.failures.length > 0 && (
          <div className="notice notice-warn">
            <p>当前版本有 {latest.failures.length} 份资料解析失败，已跳过，其余资料正常发布：</p>
            <ul>{latest.failures.map((f) => <li key={f.document_id}>{f.title}：{f.message || f.error}</li>)}</ul>
          </div>
        )}
      </section>

      {releases && releases.releases.length > 0 && (
        <section className="settings-block">
          <h2>发布历史</h2>
          <ol className="releases">
            {releases.releases.map((release) => (
              <li key={release.id} className={release.id === releases.active ? "is-active" : ""}>
                <span className="release-when">{when(release.created)}</span>
                <span className="release-what">
                  {release.documents} 份资料，{release.chunks ?? "?"} 段
                  {release.reused !== null && release.embedded !== null ? `；复用 ${release.reused} 份，新处理 ${release.embedded} 份` : ""}
                  {release.failures.length ? `；${release.failures.length} 份失败` : ""}
                </span>
                {release.id === releases.active ? (
                  <span className="tag tag-published">线上版本</span>
                ) : (
                  <button className="text-button" disabled={busy} onClick={() => {
                    if (window.confirm("切换到这个版本？问答会立即使用它的资料快照；已撤销的权限不会恢复。"))
                      void act(() => api.rollback(c, release.id), "已切换线上版本。");
                  }}>切换到此版本</button>
                )}
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
