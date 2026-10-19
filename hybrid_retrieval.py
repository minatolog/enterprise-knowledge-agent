
from collections import defaultdict
from sentence_transformers import CrossEncoder
import jieba
from rank_bm25 import BM25Okapi

from retrieval import retrieve_top_k
from rag import build_chunks


# 读取知识库中的全部文档并切块
chunks = build_chunks("data")

# 构造关键词检索语料
texts = [
    f'{chunk["section"]}\n{chunk["text"]}'
    for chunk in chunks
]

# 中文分词
tokenized_corpus = [
    list(jieba.cut(text))
    for text in texts
]

# 创建 BM25 检索器
bm25 = BM25Okapi(tokenized_corpus)

reranker = CrossEncoder(
    "BAAI/bge-reranker-base"
)

def retrieve_bm25(question: str, k: int = 5):
    tokens = list(jieba.cut(question))
    scores = bm25.get_scores(tokens)

    ranked_indices = sorted(
        range(len(chunks)),
        key=lambda i: scores[i],
        reverse=True
    )

    results = []

    for index in ranked_indices[:k]:
        chunk = chunks[index]

        results.append({
            "text": (
                f'{chunk["section"]}\n'
                f'{chunk["text"]}'
            ),
            "source": chunk["source"],
            "section": chunk["section"],
            "bm25_score": float(scores[index])
        })

    return results



def retrieve_hybrid(question: str, k: int = 3):
    # 使用更多候选，方便融合
    candidate_k = 10

    vector_results = retrieve_top_k(
        question,
        k=candidate_k
    )

    keyword_results = retrieve_bm25(
        question,
        k=candidate_k
    )

    # RRF: Reciprocal Rank Fusion
    rrf_scores = defaultdict(float)
    candidates = {}

    def add_results(results):
        for rank, item in enumerate(results, start=1):
            key = (
                item["source"],
                item["section"]
            )

            # 用排名融合，而非直接比较原始分数
            rrf_scores[key] += 1 / (60 + rank)
            candidates[key] = item

    add_results(vector_results)
    add_results(keyword_results)

    ranked = sorted(
        rrf_scores,
        key=lambda key: rrf_scores[key],
        reverse=True
    )

    final_results = []

    for key in ranked[:k]:
        item = candidates[key].copy()
        item["rrf_score"] = rrf_scores[key]
        final_results.append(item)

    return final_results


if __name__ == "__main__":

    questions = [
        "员工一年有多少天年假？",
        "输错十次密码之后账号会怎么样？",
        "输入十次错误密码",
        "输错多少次密码会被锁定？锁多久？"
    ]

    for question in questions:
        print(f"\n问题：{question}")

        results = retrieve_hybrid(question, k=3)

        for rank, result in enumerate(results, 1):
            print(
                f"{rank}. "
                f'{result["source"]} > '
                f'{result["section"]} | '
                f'RRF={result["rrf_score"]:.4f}'
            )

def retrieve_with_reranker(
    question: str,
    k: int = 3,
    candidate_k: int = 5
) -> list[dict]:

    # 1. Hybrid Search 召回候选文档
    candidates = retrieve_hybrid(
        question,
        k=candidate_k
    )

    if not candidates:
        return []

    # 2. 构建 Cross-Encoder 输入
    pairs = [
        (question, item["text"])
        for item in candidates
    ]

    # 3. 对问题和候选文档进行相关性打分
    scores = reranker.predict(pairs)

    # 4. 写入重排序分数
    for item, score in zip(candidates, scores):
        item["rerank_score"] = float(score)

    # 5. 根据 Cross-Encoder 分数重新排序
    ranked = sorted(
        candidates,
        key=lambda item: item["rerank_score"],
        reverse=True
    )

    return ranked[:k]

if __name__ == "__main__":

    question = "输错十次密码之后账号会怎么样？"

    print("\n=== Hybrid Search ===")

    hybrid_results = retrieve_hybrid(
        question,
        k=5
    )

    for i, result in enumerate(hybrid_results, 1):
        print(
            f'{i}. {result["source"]} > '
            f'{result["section"]} | '
            f'RRF={result["rrf_score"]:.4f}'
        )

    print("\n=== Hybrid + Reranker ===")

    reranked_results = retrieve_with_reranker(
        question,
        k=3,
        candidate_k=5
    )

    for i, result in enumerate(reranked_results, 1):
        print(
            f'{i}. {result["source"]} > '
            f'{result["section"]} | '
            f'Rerank={result["rerank_score"]:.4f}'
        )