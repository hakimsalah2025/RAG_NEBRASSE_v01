import requests

# عنوان الخادم المحلي لـ LM Studio
BASE_URL = "http://127.0.0.1:1234/v1"

# 1️⃣ اختبار عرض النماذج المتوفرة
models = requests.get(f"{BASE_URL}/models").json()
print("✅ النماذج المتاحة:", [m['id'] for m in models.get('data', [])])

# 2️⃣ اختبار توليد نص بسيط
response = requests.post(
    f"{BASE_URL}/chat/completions",
    json={
        "model": "mistralai/mistral-7b-instruct-v0.3",
        "messages": [
            {"role": "user", "content": "اكتب جملة قصيرة عن أهمية الذكاء الاصطناعي."}
        ],
        "max_tokens": 50
    }
).json()

print("\n🧠 رد النموذج:\n", response["choices"][0]["message"]["content"])

# 3️⃣ اختبار التضمين (Embedding)
embed_test = requests.post(
    f"{BASE_URL}/embeddings",
    json={
        "model": "text-embedding-nomic-embed-text-v1.5",  # ✅ النموذج الصحيح للتضمين
        "input": "الذكاء الاصطناعي هو فرع من علوم الحاسوب."
    }
).json()

print("\n🔢 طول متجه التضمين:", len(embed_test["data"][0]["embedding"]))
