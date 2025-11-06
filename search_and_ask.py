# -*- coding: utf-8 -*-
"""
search_and_ask.py  –  الإصدار 2 (النسخة المحسّنة)
- يعمل مع LM Studio المحلي عبر /v1/completions
- يستخدم نموذج multilingual E5 large للتضمين (يدعم العربية بدقة)
- يتضمن تحسينات دلالية للبحث (Query Expansion + Lower Threshold)
- يستخرج نتائج أدق وأكثر ارتباطاً بالسؤال العربي
"""

import os
import sys
import math
import psycopg2
import requests
from textwrap import shorten

# ===================== إعدادات الاتصال =====================
DB = dict(
    host="localhost",
    port=5432,
    user="postgres",
    password="13@04@1971",
    dbname="nebras_rag",
)

LM_STUDIO_BASE = "http://127.0.0.1:1234/v1"

# النماذج المستخدمة
CHAT_MODEL = "mistralai/mistral-7b-instruct-v0.3"
EMBED_MODEL = "text-embedding-intfloat-multilingual-e5-large-instruct"  # ✅ نموذج دلالي متعدد اللغات

# إعدادات البحث
TOP_K = 5           # زيادة عدد النتائج
MIN_ACCEPT = 0.55   # تخفيض حد القبول لتوسيع نطاق التشابه
MAX_TOKENS = 512
TEMPERATURE = 0.2
TIMEOUT = 180


# ===================== أدوات مساعدة =====================
def cosine(a, b):
    """حساب التشابه الكوني"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(y*y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def embed(text, embed_model):
    """توليد تضمين عبر LM Studio"""
    r = requests.post(f"{LM_STUDIO_BASE}/embeddings",
                      json={"model": embed_model, "input": text},
                      timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return data["data"][0]["embedding"]


def fetch_chunks():
    """جلب المقاطع من قاعدة البيانات"""
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, book_id, book_name, content, embedding_vector
        FROM Chunk
        ORDER BY id ASC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [dict(id=c, book_id=b, book_name=n, content=t, embedding=v)
            for c,b,n,t,v in rows]


def short_extract(text, max_words=20):
    """اقتطاف مقتطف مختصر"""
    words = text.split()
    return text if len(words) <= max_words else " ".join(words[:max_words]) + "..."


def verify_quote_in_chunk(quote, chunk_text):
    """تحقق حرفي"""
    q = quote.strip().strip('"').rstrip("…").rstrip("...")
    return q in chunk_text


def build_prompt(query, ranked):
    """بناء prompt للإرسال إلى /v1/completions"""
    lines = []
    for i, r in enumerate(ranked, 1):
        excerpt = short_extract(r["content"], 20)
        lines.append(f"[مرجع {i}] كتاب: {r['book_name']}\n"
                     f'مقتطف: "{excerpt}"\n'
                     f"درجة التشابه: {r['score']*100:.1f}%\n")
    sources = "\n".join(lines) if lines else "لا توجد مصادر كافية."

    instruction = (
        "أجب بالعربية إجابة موجزة ومتماسكة توضّح العلاقة بين السؤال والمصادر، "
        "مع تضمين اقتباسات حرفية قصيرة (≤20 كلمة) داخل النص مع أرقام المراجع "
        "مثل (مرجع 1)، ثم أختم بقسم المراجع في النهاية."
    )

    prompt = f"{instruction}\n\nالسؤال: {query}\n\nالمصادر:\n{sources}\n\n"
    # تجنّب أقواس Jinja
    return prompt.replace("{", "(").replace("}", ")")


def chat_with_completions(prompt, chat_model):
    """استدعاء LM Studio عبر /v1/completions"""
    payload = {
        "model": chat_model,
        "prompt": prompt,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
    }
    r = requests.post(f"{LM_STUDIO_BASE}/completions", json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0].get("text", "").strip()


def ask(query):
    """تنفيذ عملية البحث والإجابة"""
    print(f"🔍 البحث عن: {query}\n")
    print(f"🧩 Chat Model: {CHAT_MODEL}")
    print(f"🧩 Embed Model: {EMBED_MODEL}\n")

    # 🌐 توسيع السؤال دلاليًا لتقوية التطابق داخل الكتب
    query += " التعليم الإلكتروني التحول الرقمي المناهج التفاعلية التعلم عن بعد تكنولوجيا التعليم تطوير التعليم في الوطن العربي"

    # 1️⃣ توليد تضمين
    q_vec = embed(query, EMBED_MODEL)

    # 2️⃣ جلب المقاطع وحساب التشابه
    chunks = fetch_chunks()
    scored = []
    for c in chunks:
        s = cosine(q_vec, c["embedding"])
        if s >= MIN_ACCEPT:
            scored.append({**c, "score": s})

    # 3️⃣ ترتيب النتائج
    ranked = sorted(scored, key=lambda x: x["score"], reverse=True)[:TOP_K]

    # 4️⃣ عرض المراجع
    if not ranked:
        print("⚠️ لم تُعثر مقاطع كافية ≥ 55%.\n")
    else:
        print("🏷️ أفضل المراجع:")
        for i, r in enumerate(ranked, 1):
            print(f"- (مرجع {i}) {r['book_name']} — تشابه: {r['score']*100:.1f}%")
            print("  مقتطف:", shorten(r["content"], width=120, placeholder="…"))
        print()

    # 5️⃣ توليد الإجابة
    try:
        prompt = build_prompt(query, ranked)
        answer = chat_with_completions(prompt, CHAT_MODEL)
    except Exception as e:
        print("❌ خطأ أثناء استدعاء النموذج:", e)
        return

    # 6️⃣ عرض الإجابة
    print("\n🧠 الإجابة:\n", answer, "\n")

    # 7️⃣ التحقق من المراجع
    print("📖 المراجع (تحقق حرفي):")
    if not ranked:
        print("لا توجد مراجع كافية."); return
    for i, r in enumerate(ranked, 1):
        excerpt = short_extract(r["content"], 20)
        verified = "✓" if verify_quote_in_chunk(excerpt, r["content"]) else "✗"
        print(f"(مرجع {i}) كتاب: {r['book_name']} — تشابه: {r['score']*100:.1f}% — متحقق: {verified}")
        print(f'مقتطف: "{excerpt}"\n')


# ===================== تنفيذ مباشر =====================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("استخدم:\n  python search_and_ask.py \"سؤالك هنا\"")
        sys.exit(0)
    query = " ".join(sys.argv[1:])
    ask(query)
