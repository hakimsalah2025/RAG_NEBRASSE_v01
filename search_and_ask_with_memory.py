# -*- coding: utf-8 -*-
"""
search_and_ask_with_memory.py
🔹 نسخة من search_and_ask تحفظ كل سؤال وإجابة في قاعدة البيانات
🔹 تستخدم الجداول: conversation و message
"""

import os
import sys
import math
import json
import psycopg2
import requests
from textwrap import shorten
from datetime import datetime

# ===================== إعدادات الاتصال =====================
DB = dict(
    host="localhost",
    port=5432,
    user="postgres",
    password="13@04@1971",
    dbname="nebras_rag",
)

LM_STUDIO_BASE = "http://127.0.0.1:1234/v1"
CHAT_MODEL = "mistralai/mistral-7b-instruct-v0.3"
EMBED_MODEL = "text-embedding-intfloat-multilingual-e5-large-instruct"

TOP_K = 5
MIN_ACCEPT = 0.55
MAX_TOKENS = 512
TEMPERATURE = 0.2
TIMEOUT = 180


# ===================== أدوات مساعدة =====================
def cosine(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(y*y for y in b))
    return 0.0 if (na == 0 or nb == 0) else dot / (na * nb)


def embed(text):
    """توليد تضمين عبر LM Studio"""
    r = requests.post(f"{LM_STUDIO_BASE}/embeddings",
                      json={"model": EMBED_MODEL, "input": text},
                      timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]


def connect_db():
    return psycopg2.connect(**DB)


def fetch_chunks():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, book_id, book_name, content, embedding_vector
        FROM chunk
        ORDER BY id ASC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [dict(id=c, book_id=b, book_name=n, content=t, embedding=v)
            for c,b,n,t,v in rows]


def short_extract(text, max_words=20):
    words = text.split()
    return text if len(words) <= max_words else " ".join(words[:max_words]) + "..."


def verify_quote_in_chunk(quote, chunk_text):
    q = quote.strip().strip('"').rstrip("…").rstrip("...")
    return q in chunk_text


def build_prompt(query, ranked):
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
    return prompt.replace("{", "(").replace("}", ")")


def chat_with_completions(prompt):
    payload = {
        "model": CHAT_MODEL,
        "prompt": prompt,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
    }
    r = requests.post(f"{LM_STUDIO_BASE}/completions", json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0].get("text", "").strip()


# ===================== إدارة قاعدة البيانات للمحادثات =====================
def ensure_conversation():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM conversation ORDER BY id DESC LIMIT 1;")
    row = cur.fetchone()
    if row:
        cid = row[0]
    else:
        cur.execute("INSERT INTO conversation (title, message_count) VALUES (%s, %s) RETURNING id;",
                    ("محادثة جديدة", 0))
        cid = cur.fetchone()[0]
        conn.commit()
    cur.close(); conn.close()
    return cid


def save_message(conversation_id, role, content, refs=None):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO message (conversation_id, role, content, references_json)
        VALUES (%s, %s, %s, %s)
    """, (conversation_id, role, content, json.dumps(refs) if refs else None))
    conn.commit()
    cur.close(); conn.close()


# ===================== المنطق الرئيسي =====================
def ask(query):
    print(f"🔍 البحث عن: {query}\n")
    print(f"🧩 Chat Model: {CHAT_MODEL}")
    print(f"🧩 Embed Model: {EMBED_MODEL}\n")

    query += " التعليم الإلكتروني التحول الرقمي المناهج التفاعلية التعلم عن بعد تكنولوجيا التعليم تطوير التعليم في الوطن العربي"
    q_vec = embed(query)
    chunks = fetch_chunks()

    scored = []
    for c in chunks:
        s = cosine(q_vec, c["embedding"])
        if s >= MIN_ACCEPT:
            scored.append({**c, "score": s})
    ranked = sorted(scored, key=lambda x: x["score"], reverse=True)[:TOP_K]

    if not ranked:
        print("⚠️ لم تُعثر مقاطع كافية ≥ 55%.\n")
    else:
        print("🏷️ أفضل المراجع:")
        for i, r in enumerate(ranked, 1):
            print(f"- (مرجع {i}) {r['book_name']} — تشابه: {r['score']*100:.1f}%")
            print("  مقتطف:", shorten(r["content"], width=120, placeholder="…"))
        print()

    prompt = build_prompt(query, ranked)
    answer = chat_with_completions(prompt)

    print("\n🧠 الإجابة:\n", answer, "\n")

    print("📖 المراجع (تحقق حرفي):")
    refs = []
    for i, r in enumerate(ranked, 1):
        excerpt = short_extract(r["content"], 20)
        verified = verify_quote_in_chunk(excerpt, r["content"])
        refs.append({
            "book_name": r["book_name"],
            "similarity": round(r["score"]*100, 2),
            "excerpt": excerpt,
            "verified": verified
        })
        print(f"(مرجع {i}) {r['book_name']} — تشابه: {r['score']*100:.1f}% — متحقق: {'✓' if verified else '✗'}")
        print(f'مقتطف: "{excerpt}"\n')

    # 💾 حفظ في قاعدة البيانات
    conv_id = ensure_conversation()
    save_message(conv_id, "user", query)
    save_message(conv_id, "assistant", answer, refs)
    print(f"💾 تم حفظ المحادثة في conversation_id = {conv_id}\n")


# ===================== تنفيذ مباشر =====================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("استخدم:\n  python search_and_ask_with_memory.py \"سؤالك هنا\"")
        sys.exit(0)
    query = " ".join(sys.argv[1:])
    ask(query)
