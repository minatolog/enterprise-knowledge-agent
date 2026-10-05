from retrieval import retrieve_best_chunk
from llm import answer_with_context


question = "员工一年有多少天年假？"

context, score = retrieve_best_chunk(question)

answer = answer_with_context(
    question=question,
    context=context
)


print("用户问题：")
print(question)

print("\n检索到的企业资料：")
print(context)

print("\n检索相似度：")
print(score)

print("\nAI 回答：")
print(answer)