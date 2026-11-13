import {
  ArrowUpRight,
  Search,
  Layers3,
  Sparkles,
  FileCheck2,
  GitBranch,
} from "lucide-react";

export const steps = [
  {
    id: "check_index",
    title: "开始",
    subtitle: "用户问题 · 索引就绪检查",
    icon: ArrowUpRight,
    color: "purple",
    description:
      "接收问题，检查知识库索引是否就绪。每次问题独立处理，不共享会话上下文。",
    x: 30,
    y: 210,
  },
  {
    id: "retrieve",
    title: "混合检索",
    subtitle: "Dense + BM25 → RRF",
    icon: Search,
    color: "blue",
    description:
      "结合语义与关键词召回，使用 RRF 融合，并由 Cross-Encoder 对召回候选精排。",
    x: 330,
    y: 210,
  },
  {
    id: "build_context",
    title: "构建上下文",
    subtitle: "Top K · 证据与来源编号",
    icon: Layers3,
    color: "teal",
    description:
      "从检索结果组装上下文，并建立来源编号映射。返回片段数量可在测试面板调整。",
    x: 650,
    y: 55,
  },
  {
    id: "generate",
    title: "回答生成",
    subtitle: "DeepSeek · 基于证据回答",
    icon: Sparkles,
    color: "purple",
    description:
      "通过服务端模型配置生成回答。当前接口不支持在页面更改模型或系统提示词。",
    x: 960,
    y: 55,
  },
  {
    id: "map_citations",
    title: "引用映射",
    subtitle: "原文 · 页码 · Chunk ID",
    icon: FileCheck2,
    color: "teal",
    description:
      "将引用编号映射至真实文件与页码。引用映射不等于答案证据支持验证。",
    x: 960,
    y: 360,
  },
  {
    id: "no_evidence",
    title: "无候选分支",
    subtitle: "跳过生成 · 返回说明",
    icon: GitBranch,
    color: "amber",
    description:
      "当检索候选为空时跳过模型生成。候选非空并不代表一定有足够证据。",
    x: 650,
    y: 360,
  },
];
