from llm_client import generate_from_llm

print("جارٍ الاتصال بـ OpenAI...\n")
answer = generate_from_llm("اشرح الذكاء الاصطناعي بلغة بسيطة.")
print("الإجابة:\n", answer)
