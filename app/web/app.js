const form = document.querySelector("#query-form");
const questionInput = document.querySelector("#question");
const topKInput = document.querySelector("#top-k");
const sendButton = document.querySelector("#send-button");
const conversation = document.querySelector("#conversation");
const formMessage = document.querySelector("#form-message");

function element(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value !== undefined) node.textContent = value;
  return node;
}

function scrollToLatest() {
  conversation.lastElementChild?.scrollIntoView({ behavior: "smooth", block: "end" });
}

function formatSource(source) {
  const card = element("div", "source-item");
  card.append(element("strong", "", source.label || source.source || "资料来源"));
  const path = source.relative_path || source.source || "路径未知";
  const page = source.page_start === source.page_end
    ? `第 ${source.page_start} 页`
    : `第 ${source.page_start}–${source.page_end} 页`;
  card.append(element("span", "", `${path} · ${page}`));
  if (source.source_url) {
    try {
      const url = new URL(source.source_url);
      if (["https:", "http:"].includes(url.protocol)) {
        const link = element("a", "", "打开官方原文 ↗");
        link.href = url.href;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        card.append(link);
      }
    } catch (_) {
      // Ignore invalid source URLs; the local path and page remain visible.
    }
  }
  return card;
}

function showAnswer(card, data) {
  card.replaceChildren(element("p", "answer-label", "知识库回答"));
  card.append(element("div", "answer-text", data.answer || "本次没有返回答案。"));
  const timings = data.timings_ms || {};
  const duration = typeof timings.total_ms === "number" ? ` · ${timings.total_ms} ms` : "";
  card.append(element("div", "answer-meta", `检索到 ${data.retrieval_count ?? 0} 个片段${duration} · 请求 ID ${data.request_id || "未知"}`));
  if (Array.isArray(data.sources) && data.sources.length) {
    const sources = element("section", "sources");
    sources.append(element("h4", "", `引用来源 (${data.sources.length})`));
    data.sources.forEach((source) => sources.append(formatSource(source)));
    card.append(sources);
  } else {
    card.append(element("div", "answer-meta", "本次回答没有明确引用来源，请谨慎使用。"));
  }
}

async function submitQuestion() {
  const question = questionInput.value.trim();
  if (!question || sendButton.disabled) return;
  formMessage.textContent = "";
  document.querySelector("#welcome")?.remove();

  const turn = element("section", "turn");
  turn.append(element("div", "question-bubble", question));
  const card = element("div", "answer-card");
  card.setAttribute("role", "status");
  card.append(element("p", "answer-label", "正在检索资料并生成回答…"));
  turn.append(card);
  conversation.append(turn);
  scrollToLatest();

  sendButton.disabled = true;
  sendButton.textContent = "正在回答…";
  questionInput.value = "";
  try {
    const response = await fetch("/api/v1/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k: Number(topKInput.value) }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || `请求失败（HTTP ${response.status}）`);
    }
    showAnswer(card, data);
  } catch (error) {
    card.classList.add("error-card");
    card.replaceChildren(element("p", "answer-label", "本次提问失败"), element("div", "answer-text", error.message || "无法连接服务，请检查后端是否在运行。"));
    formMessage.textContent = "请检查索引、API Key 或网络状态后重试。";
  } finally {
    sendButton.disabled = false;
    sendButton.textContent = "发送问题 ↗";
    questionInput.focus();
    scrollToLatest();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  submitQuestion();
});
questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    form.requestSubmit();
  }
});
document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    questionInput.value = button.dataset.question;
    questionInput.focus();
  });
});

async function loadStatus() {
  const badge = document.querySelector("#service-status");
  const indexMessage = document.querySelector("#index-message");
  try {
    const health = await fetch("/health");
    if (!health.ok) throw new Error("服务未就绪");
    badge.textContent = "运行中";
    badge.classList.add("ok");
  } catch (_) {
    badge.textContent = "无法连接";
    badge.classList.add("error");
    indexMessage.textContent = "请启动后端服务并刷新页面。";
    return;
  }
  try {
    const response = await fetch("/api/v1/documents");
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || "索引未就绪");
    document.querySelector("#document-count").textContent = data.indexed_document_count;
    document.querySelector("#chunk-count").textContent = data.indexed_chunk_count;
    const list = document.querySelector("#document-list");
    list.replaceChildren();
    data.documents.forEach((documentInfo) => {
      list.append(element("li", "", `${documentInfo.relative_path || documentInfo.source} · ${documentInfo.chunk_count} 片段`));
    });
    if (!data.documents.length) list.append(element("li", "", "当前没有已索引文档"));
  } catch (error) {
    indexMessage.textContent = error.message || "无法读取索引状态。";
    document.querySelector("#document-list").replaceChildren(element("li", "muted", "索引未就绪"));
  }
}

loadStatus();
