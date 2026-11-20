import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { api, safeLink, type ManagedDocument } from "../api";
import type { Assistant } from "../state/useAssistant";

const CHUNKER_NAMES: Record<string, string> = { structured: "按条款切分", page: "按页切分" };

function LocalLibrary({ assistant }: { assistant: Assistant }) {
  const { documents, config, health } = assistant;
  if (health === "offline")
    return (
      <div className="notice notice-error">
        <p>本地服务没有响应。在项目目录运行 <code>python -m uvicorn app.api:app --port 8020</code>，然后刷新。</p>
      </div>
    );
  return (
    <>
      {documents ? (
        <>
          <p className="lead">
            {documents.indexed_document_count} 份文件，切成 {documents.indexed_chunk_count} 段建立索引。只有这些文件里的内容会被用来回答问题。
          </p>
          <table className="table">
            <thead>
              <tr>
                <th scope="col">文件</th>
                <th scope="col">页码</th>
                <th scope="col" className="num">段数</th>
                <th scope="col">切分方式</th>
              </tr>
            </thead>
            <tbody>
              {documents.documents.map((doc) => {
                const link = safeLink(doc.source_url);
                return (
                  <tr key={doc.relative_path}>
                    <td>
                      <span className="doc-title">{doc.title || doc.source}</span>
                      <span className="doc-path">{link ? <a href={link} target="_blank" rel="noreferrer">{doc.relative_path}</a> : doc.relative_path}</span>
                    </td>
                    <td>{doc.page_start ? `${doc.page_start}–${doc.page_end}` : "—"}</td>
                    <td className="num">{doc.chunk_count}</td>
                    <td>{CHUNKER_NAMES[doc.chunker || "page"] || doc.chunker}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {config && documents.documents.some((d) => (d.chunker || "page") !== config.chunker) && (
            <div className="notice notice-warn">
              <p>
                服务配置为“{CHUNKER_NAMES[config.chunker]}”，但现有索引仍是旧格式。运行 <code>python index_documents.py</code> 重建索引后，检索和评测才对应当前配置。
              </p>
            </div>
          )}
        </>
      ) : (
        <div className="notice notice-warn">
          <p>还没有可用的索引。在项目目录运行 <code>python index_documents.py</code>。</p>
        </div>
      )}
      {config && (
        <section className="settings-block">
          <h2>检索配置</h2>
          <dl className="facts">
            <dt>向量模型</dt><dd>{config.embedding_model}</dd>
            <dt>重排模型</dt><dd>{config.reranker_model}</dd>
            <dt>重排候选数</dt><dd>{config.candidate_k} 段</dd>
            <dt>拒答线</dt><dd>相关度低于 {config.min_rerank_score} 时不调用模型，直接拒答</dd>
            <dt>繁简归一</dt><dd>{config.t2s_backend === "opencc" ? "OpenCC" : "内置字表（安装 opencc 后更完整）"}</dd>
            <dt>回答模型</dt><dd>{config.llm_model}{config.llm_configured ? "" : "（未配置 DEEPSEEK_API_KEY）"}</dd>
          </dl>
        </section>
      )}
    </>
  );
}

function EnterpriseLibrary({ assistant }: { assistant: Assistant }) {
  const [docs, setDocs] = useState<ManagedDocument[] | null>(null);
  const [error, setError] = useState("");
  const load = () => {
    setError("");
    api.managedDocuments(assistant.connection).then(setDocs).catch((e) => setError(e.message));
  };
  useEffect(load, [assistant.connection]);
  if (error) return <div className="notice notice-error"><p>{error}</p></div>;
  if (!docs) return <p className="lead">正在读取资料清单…</p>;
  if (!docs.length) return <p className="lead">你的账号目前没有可查看的资料。</p>;
  return (
    <>
      <p className="lead">你有权限查看 {docs.length} 份资料。问答只会检索其中已发布的版本。</p>
      <table className="table">
        <thead><tr><th scope="col">资料</th><th scope="col">可见用户组</th><th scope="col">状态</th></tr></thead>
        <tbody>
          {docs.map((doc) => (
            <tr key={doc.id}>
              <td><span className="doc-title">{doc.title}</span><span className="doc-path">第 {doc.version} 版</span></td>
              <td>{doc.groups.join("、")}</td>
              <td><StatusTag status={doc.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

export function StatusTag({ status }: { status: ManagedDocument["status"] }) {
  const copy = { published: "已发布", pending: "待发布", failed: "解析失败" }[status];
  return <span className={`tag tag-${status}`}>{copy}</span>;
}

export default function Library({ assistant }: { assistant: Assistant }) {
  return (
    <div className="page">
      <header className="page-head">
        <h1>知识库</h1>
        {assistant.prefs.mode === "local" && (
          <button className="text-button" onClick={() => void assistant.refreshLocal()}>
            <RefreshCw size={14} /> 刷新
          </button>
        )}
      </header>
      {assistant.prefs.mode === "enterprise" ? <EnterpriseLibrary assistant={assistant} /> : <LocalLibrary assistant={assistant} />}
    </div>
  );
}
