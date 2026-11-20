import { useState } from "react";
import { api, type Me } from "../api";
import type { Assistant } from "../state/useAssistant";

export default function Settings({ assistant }: { assistant: Assistant }) {
  const { prefs, setPrefs } = assistant;
  const [draftToken, setDraftToken] = useState(assistant.token);
  const [check, setCheck] = useState<{ me?: Me; error?: string } | null>(null);

  return (
    <div className="page">
      <header className="page-head"><h1>设置</h1></header>

      <section className="settings-block">
        <h2>知识库</h2>
        <fieldset className="choice">
          <legend className="visually-hidden">选择知识库</legend>
          <label className={prefs.mode === "local" ? "is-checked" : ""}>
            <input type="radio" name="mode" checked={prefs.mode === "local"} onChange={() => setPrefs({ mode: "local" })} />
            <span className="choice-title">本地知识库</span>
            <span className="choice-desc">7 份公开制度文件，单人使用，不需要登录。对应 <code>/api/v1</code>。</span>
          </label>
          <label className={prefs.mode === "enterprise" ? "is-checked" : ""}>
            <input type="radio" name="mode" checked={prefs.mode === "enterprise"} onChange={() => setPrefs({ mode: "enterprise" })} />
            <span className="choice-title">企业知识库</span>
            <span className="choice-desc">按租户和用户组控制可见范围，支持上传、发布和版本回滚。对应 <code>/api/v2</code>，需要令牌。</span>
          </label>
        </fieldset>
        <p className="footnote">切换后，新的提问会开启新对话；已有对话保留在左侧。</p>
      </section>

      {prefs.mode === "enterprise" && (
        <section className="settings-block">
          <h2>企业令牌</h2>
          <form
            className="token-form"
            onSubmit={async (event) => {
              event.preventDefault();
              assistant.setToken(draftToken.trim());
              try {
                setCheck({ me: await api.me({ mode: "enterprise", token: draftToken.trim() }) });
              } catch (e) {
                setCheck({ error: (e as Error).message });
              }
            }}
          >
            <label htmlFor="token">Bearer 令牌</label>
            <textarea id="token" rows={3} value={draftToken} spellCheck={false} onChange={(e) => setDraftToken(e.target.value)} placeholder="粘贴 OIDC 或开发令牌" />
            <label className="check">
              <input type="checkbox" checked={prefs.rememberToken} onChange={(e) => setPrefs({ rememberToken: e.target.checked })} />
              在这台电脑上记住令牌（默认只保留到关闭标签页）
            </label>
            <button className="primary">保存并验证</button>
            {check?.me && <p className="field-ok">已验证：{check.me.subject}，租户 {check.me.tenant}，角色 {check.me.roles.join("、") || "普通用户"}</p>}
            {check?.error && <p className="field-error">{check.error}</p>}
          </form>
        </section>
      )}

      <section className="settings-block">
        <h2>回答</h2>
        <label className="row">
          每次引用的资料段数
          <select value={prefs.topK} onChange={(e) => setPrefs({ topK: Number(e.target.value) })}>
            {[3, 5, 8].map((v) => <option key={v} value={v}>{v} 段</option>)}
          </select>
        </label>
        <p className="footnote">段数越多，回答能覆盖跨文件的问题，但更慢，也更容易混入无关内容。</p>
      </section>

      <section className="settings-block">
        <h2>对话记录</h2>
        <label className="check">
          <input type="checkbox" checked={prefs.saveHistory} onChange={(e) => setPrefs({ saveHistory: e.target.checked })} />
          把对话保存在这个浏览器里
        </label>
        {assistant.storageError && <p className="field-error">{assistant.storageError}</p>}
        <button className="text-button danger" onClick={() => {
          if (window.confirm("清空全部对话记录？")) assistant.clearHistory();
        }}>清空对话记录</button>
      </section>
    </div>
  );
}
