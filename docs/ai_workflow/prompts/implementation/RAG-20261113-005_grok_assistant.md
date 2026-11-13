# RAG-20261113-005 用户原始附件

日期2026-11-13，Codex / GPT-6（具体变体未知）。以下逐字保存本次实际可读取的粘贴附件内容，无脱敏。原件路径：/Users/luogewen/.codex/attachments/8f1a0018-8d79-4725-ba8f-87a286714225/已粘贴的文本.txt。附件末尾截断在“Verify that the generated answer is”，未取得后续内容，不补写。

---

# Task: Upgrade Enterprise RAG Frontend to a Grok-Inspired AI Knowledge Assistant

## 1. Project Objective

I want to redesign and upgrade the frontend of my existing Enterprise RAG project into a professional AI Knowledge Assistant interface.

Use the following project as the primary visual and interaction reference:

- Grok Clone Live Demo: https://ai-website-clone-1761067857895.vercel.app/
- Reference Repository: https://github.com/bhaktofmahakal/UI-Engineering

The goal is NOT to create a simple visual clone.

The goal is to build a professional enterprise-grade RAG application that combines Grok-inspired UI/UX with the existing RAG backend and retrieval capabilities.

Product name: **CNOOC Enterprise Knowledge Assistant**

## 2. Critical Requirement: Inspect Before Modifying

Before writing any code:

1. Inspect the entire existing project structure.
2. Identify the current frontend framework, libraries and entry points.
3. Identify the backend framework and existing API endpoints.
4. Understand how the frontend currently communicates with the backend.
5. Inspect the existing RAG pipeline and response data structures.
6. Check existing documentation, development logs and project conventions.
7. Check Git status and preserve all existing user changes.

Do not assume API endpoints, response formats or project structure.

Do not rewrite or replace existing backend functionality.

First provide a concise implementation plan based on the actual codebase. Then proceed with implementation unless a significant architectural blocker requires clarification.

## 3. Existing RAG Architecture

The existing project already has a working RAG pipeline.

Current architecture:

PDF Documents
→ PDF Parsing and Chunking
→ ChromaDB Vector Retrieval
+
BM25 Keyword Retrieval
→ Reciprocal Rank Fusion (RRF)
→ Cross-Encoder Reranking
→ DeepSeek Answer Generation
→ Source Attribution

Current knowledge base:

- Official CNOOC documents only.
- ChromaDB Collection: cnooc_knowledge.
- 7 indexed documents.
- 106 PDF pages.
- 194 chunks.
- Each chunk contains a stable ID, source path and PDF page number.
- Answers should include document provenance and page references.

Important: The frontend must integrate with the existing implementation rather than creating a new mock RAG system.

## 4. UI/UX Design Requirements

Use Grok Clone as the main visual reference.

### A. Overall Visual Style

Design direction:

- Dark-first interface.
- Modern AI product aesthetic.
- Charcoal and black background.
- Subtle borders and surface contrasts.
- Carefully selected blue accent colors.
- Clean typography and consistent spacing.
- Smooth but restrained animations.
- Minimalist, professional and premium appearance.

Avoid:
- Excessive gradients.
- Excessive glassmorphism.
- Overly colorful dashboard cards.
- Unnecessary decorative elements.
- Generic AI-generated dashboard appearance.

The final interface should look like a real commercial AI SaaS product.

### B. Left Sidebar

Implement a collapsible navigation sidebar.

Include:

- Product logo and name.
- New Chat button.
- Conversation history.
- Search conversations.
- Recent conversations grouped by date.
- Settings entry.
- Knowledge Base entry.

Conversation history should be based on actual persisted data if available.

Do not introduce fake persistence.

### C. Main Chat Interface

The chat interface is the core of the application.

Initial empty state:

- Product introduction.
- Welcome message.
- Short explanation of the knowledge assistant.
- Several suggested questions.

Suggested questions:

1. What are the company's major compliance requirements?
2. Summarize the corporate governance structure.
3. What are the key responsibilities of the board of directors?
4. Find the relevant provisions concerning internal controls.

Chat interaction:

- User messages aligned consistently.
- Assistant responses with readable Markdown formatting.
- Code blocks where necessary.
- Proper paragraph spacing.
- Loading indicators.
- Error handling.
- Auto-scroll to the latest message.
- Copy answer functionality.
- Regenerate answer if supported by the backend.
- Enter to send, Shift + Enter for a new line.

The interface should feel natural and responsive, similar to a modern AI chatbot.

### D. Input Composer

Create a polished message composer at the bottom of the chat.

Include:

- Multiline text input.
- Send button.
- Keyboard interaction.
- Disabled state when submitting.
- Loading state while generating.

File upload should only be implemented if the existing backend supports it.

Do not create buttons that look functional but have no actual implementation.

### E. RAG Source Attribution (Very Important)

This is where our application should go beyond an ordinary chatbot.

The assistant must clearly display the sources used to generate its answers.

For example:

Answer:

"According to the relevant corporate governance documentation..."

Sources:

- Document: CNOOC Corporate Governance Policy
- Page: 12
- Source path: data/cnooc/...
- Relevant retrieved content.

Requirements:

1. Display source references alongside assistant answers.
2. Make source references clickable.
3. Allow users to expand source details.
4. Display the original document name and page number.
5. Show retrieved text snippets when available.
6. Support multiple sources per answer.

If the backend already returns retrieval scores, display them in an optional technical details panel.

Never invent retrieval scores, source documents or page numbers.

If source metadata is unavailable, identify the missing backend field instead of generating fake information.

### F. Retrieval Details Panel

Implement an optional expandable panel for technical transparency.

It should display the actual available retrieval information:

- Retrieved documents.
- BM25 retrieval results.
- Vector retrieval results.
- RRF fusion results.
- Cross-Encoder reranking results.
- Final source references.

Only expose information that the backend actually provides.

The panel should be unobtrusive by default.

This feature is particularly important because the project is intended to demonstrate enterprise RAG engineering capabilities.

### G. Knowledge Base Page

Create a separate knowledge base management page.

Display available information:

- Number of indexed documents.
- Number of PDF pages.
- Number of indexed chunks.
- Document names.
- Document categories.
- Indexing status.
- Last update time, if available.

Support document inspection and basic search if existing APIs allow it.

Do not implement destructive document operations without confirming their backend support.

### H. Responsive Design

Support:

- Desktop.
- Laptop.
- Tablet.
- Mobile.

The sidebar should become a mobile drawer on smaller screens.

The chat composer should remain accessible.

## 5. Technical Requirements

1. Reuse the existing frontend framework and dependencies.
2. Follow the current project's coding conventions.
3. Build reusable components.
4. Separate UI components from API service logic.
5. Keep API integration independent of presentation components.
6. Handle loading, empty and error states.
7. Avoid unnecessary dependencies.
8. Preserve existing backend APIs.
9. Do not introduce hardcoded mock responses into production code.
10. Ensure the application builds and runs successfully.

Suggested component organization, adapted to the existing project:

- Sidebar
- ChatLayout
- ChatHeader
- WelcomeScreen
- MessageList
- UserMessage
- AssistantMessage
- MessageComposer
- SourceCitation
- SourceDetailPanel
- RetrievalDetailsPanel
- KnowledgeBasePage
- SettingsPage

## 6. Engineering Quality

The project should remain maintainable and extensible.

Avoid putting all UI logic into one large component.

Use appropriate component boundaries and reusable hooks.

Keep API calls, message state and rendering logic separated.

Preserve existing functionality.

Do not make unnecessary backend changes.

Do not remove existing documentation or development logs.

Follow the project's existing prompt-management and development-log conventions when recording this task.

## 7. Testing and Acceptance Criteria

After implementation:

1. Start the frontend successfully.
2. Verify that the application communicates with the existing backend.
3. Send a real question to the RAG system.
4. Verify that the generated answer is