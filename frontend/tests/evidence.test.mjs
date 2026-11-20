import test from "node:test";
import assert from "node:assert/strict";
import {
  citedNumbers,
  evidenceOf,
  historyFrom,
  linkCitations,
  sentencesCiting,
  supportingRanges,
} from "../src/utils/evidence.ts";
import { fold } from "../src/utils/t2s.ts";

const source = (id, extra = {}) => ({
  chunk_id: id, source: `${id}.pdf`, relative_path: `${id}.pdf`, page_start: 1, page_end: 1,
  source_url: null, label: id, rerank_score: 0.9, ...extra,
});

test("citations are numbered in order of first appearance and become chips", () => {
  const answer = "每季度至少开会一次。[资料 2] 文件提前三天发送[资料 1][资料 2]。";
  assert.deepEqual(citedNumbers(answer), [2, 1]);
  assert.equal(linkCitations("规定[资料 3]"), "规定[3](#cite-3)");
});

test("citation N points at the N-th retrieved chunk, not the N-th cited source", () => {
  const retrieved = [source("a"), source("b"), source("c")];
  const result = {
    request_id: "r", answer: "甲[资料 3]，乙[资料 1]", retrieval_count: 3, timings_ms: {},
    sources: [retrieved[2], retrieved[0]], retrieved,
  };
  const evidence = evidenceOf(result);
  assert.equal(evidence.indexOfCitation(3), 2);
  assert.equal(evidence.indexOfCitation(1), 0);
  assert.equal(evidence.indexOfCitation(2), -1);
  assert.ok(evidence.cited.has("c") && !evidence.cited.has("b"));
});

test("answers stored before 'retrieved' existed still map citations", () => {
  const result = { request_id: "r", answer: "甲[资料 2]", retrieval_count: 1, timings_ms: {}, sources: [source("x")] };
  assert.equal(evidenceOf(result).indexOfCitation(2), 0);
});

test("supporting text is found across Traditional script and punctuation", () => {
  assert.equal(fold("審核委員會"), "审核委员会");
  const text = "4. 審核委員會每季度至少召開一次會議，所有會議文件需在每次開會前至少三天發送。";
  const claims = sentencesCiting("审核委员会每季度至少召开一次会议。[资料 1] 其他内容。", 1);
  assert.deepEqual(claims, ["审核委员会每季度至少召开一次会议。"]);
  const [[start, end]] = supportingRanges(text, claims);
  assert.equal(text.slice(start, end), "審核委員會每季度至少召開一次會議");
});

test("history sent to the API skips refusals and strips citation markers", () => {
  const turns = [
    { question: "问一", result: { answer: "答一[资料 1]", status: "answered" } },
    { question: "问二", result: { answer: "无法回答", status: "refused" } },
    { question: "问三", error: "失败" },
  ];
  assert.deepEqual(historyFrom(turns), [
    { role: "user", content: "问一" },
    { role: "assistant", content: "答一" },
  ]);
});
