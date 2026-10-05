from retrieval import retrieve_top_k
from llm import answer_with_context


question = "年假应该怎么申请，没用完怎么办？"

results = retrieve_top_k(question, k=3)

contexts = []

for result in results:
    # 检索结果还包含来源和章节；发送给模型的是正文文字。
    contexts.append(result["text"])

context = "\n\n".join(contexts)

answer = answer_with_context(
    question=question,
    context=context
)


print("用户问题：")
print(question)

print("\n检索资料：")

for i, result in enumerate(results, start=1):
    print(f"\n--- Chunk {i} ---")
    print(f"相似度：{result['score']:.4f}")
    print(f"来源：{result['source']}，章节：{result['section']}")
    print(result["text"])

print("\nAI 回答：")
print(answer)
