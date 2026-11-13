import test from "node:test";
import assert from "node:assert/strict";
import {
  parseHistory,
  serializeHistory,
  dateGroup,
} from "../src/state/conversations.ts";
import { safeLink } from "../src/api.ts";
const turn = {
  id: "t1",
  question: "test question",
  topK: 3,
  createdAt: "2026-11-13T10:00:00+11:00",
  result: {
    request_id: "req-1",
    answer: "**Evidence**",
    sources: [
      {
        chunk_id: "id1",
        source: "test.pdf",
        relative_path: "test.pdf",
        page_start: 2,
        page_end: 3,
        source_url: "https://example.invalid/test.pdf",
        label: "test",
        rerank_score: 0.3,
      },
    ],
    retrieval_count: 1,
    timings_ms: { total_ms: 25 },
  },
};
const conversation = {
  id: "c1",
  title: "test",
  createdAt: turn.createdAt,
  updatedAt: turn.createdAt,
  turns: [turn],
};
test("restore actual answer metadata after serialization, excluding empty chats", () => {
  const empty = { ...conversation, id: "empty", turns: [] };
  assert.deepEqual(parseHistory(serializeHistory([empty, conversation])), [
    conversation,
  ]);
});
test("reject malformed, unknown-version and oversized storage without crashing", () => {
  for (const raw of [
    "{",
    JSON.stringify({ version: 2, conversations: [conversation] }),
    "a".repeat(5_000_001),
    JSON.stringify({
      version: 1,
      conversations: [
        {
          ...conversation,
          turns: [{ ...turn, result: { ...turn.result, sources: [{}] } }],
        },
      ],
    }),
  ])
    assert.deepEqual(parseHistory(raw), []);
});
test("discard corrupted scores and timings instead of showing invented values", () => {
  for (const result of [
    { ...turn.result, timings_ms: { total_ms: "NaN" } },
    {
      ...turn.result,
      sources: [{ ...turn.result.sources[0], rerank_score: "0.9" }],
    },
  ])
    assert.equal(
      parseHistory(
        JSON.stringify({
          version: 1,
          conversations: [{ ...conversation, turns: [{ ...turn, result }] }],
        }),
      ).length,
      0,
    );
});
test("deduplicate identities and bound persisted message count", () => {
  assert.equal(
    parseHistory(
      JSON.stringify({
        version: 1,
        conversations: [conversation, conversation],
      }),
    ).length,
    1,
  );
  const many = {
    ...conversation,
    turns: Array.from({ length: 120 }, (_, i) => ({ ...turn, id: `t-${i}` })),
  };
  assert.equal(parseHistory(serializeHistory([many]))[0].turns.length, 100);
});
test("only actual absolute http(s) URLs can become source or Markdown links", () => {
  for (const link of [
    "javascript:alert(1)",
    "data:text/html,<h1>x</h1>",
    "file:///etc/passwd",
    "/relative",
    "//example.invalid",
  ])
    assert.equal(safeLink(link), undefined);
  assert.equal(
    safeLink("https://example.invalid/a#page=2"),
    "https://example.invalid/a#page=2",
  );
});
test("conversation groups follow local calendar dates", () => {
  const now = new Date(2026, 10, 13, 12);
  assert.equal(dateGroup(new Date(2026, 10, 13, 9).toISOString(), now), "今天");
  assert.equal(
    dateGroup(new Date(2026, 10, 12, 23).toISOString(), now),
    "昨天",
  );
});
