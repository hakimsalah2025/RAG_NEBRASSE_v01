# -*- coding: utf-8 -*-
"""
chat_ui.py
💬 واجهة دردشة رسومية بالعربية باستخدام Streamlit – مهيأة لـ Qwen2.5-7B-Instruct-1M-GGUF
"""

import streamlit as st
import psycopg2
import requests
import json
import math

# ===================== إعدادات الاتصال =====================
DB = dict(
    host="localhost",
    port=5432,
    user="postgres",
    password="13@04@1971",
    dbname="nebras_rag",
)

LM_STUDIO_BASE = "http://127.0.0.1:1234/v1"
CHAT_MODEL = "Qwen2.5-7B-Instruct-1M-GGUF"
EMBED_MODEL = "text-embedding-intfloat-multilingual-e5-large-instruct"

LANGUAGE_HINT = "اللغة العربية الفصحى الأكاديمية"
TOP_K = 5
MIN_ACCEPT = 0.8
TEMPERATURE = 0.2
MAX_TOKENS = 1024


# ===================== أدوات مساعدة =====================
def connect_db():
    return psycopg2.connect(**DB)


def cosine(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return 0.0 if (na == 0 or nb == 0) else dot / (na * nb)


def embed(text):
    """توليد تضمين عبر LM Studio"""
    r = requests.post(f"{LM_STUDIO_BASE}/embeddings",
                      json={"model": EMBED_MODEL, "input": text})
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]


def fetch_chunks():
    """جلب كل المقاطع المخزّنة"""
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, book_id, book_name, content, start_line, end_line, embedding_vector
        FROM chunk
        ORDER BY id ASC;
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [dict(id=c, book_id=b, book_name=n, content=t,
                 start_line=s, end_line=e, embedding=v)
            for c, b, n, t, s, e, v in rows]


def short_extract(text, max_words=20):
    words = text.split()
    return text if len(words) <= max_words else " ".join(words[:max_words]) + "..."


def save_message(conversation_id, role, content, refs=None):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO message (conversation_id, role, content, references_json)
        VALUES (%s, %s, %s, %s)
    """, (conversation_id, role, content, json.dumps(refs) if refs else None))
    conn.commit()
    cur.close(); conn.close()


def ensure_conversation():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO conversation (title, message_count) VALUES (%s, %s) RETURNING id;",
                ("محادثة من Streamlit", 0))
    cid = cur.fetchone()[0]
    conn.commit()
    cur.close(); conn.close()
    return cid


def search_chunks(query):
    q_vec = embed(query)
    chunks = fetch_chunks()
    results = []
    for c in chunks:
        s = cosine(q_vec, c["embedding"])
        if s >= MIN_ACCEPT:
            results.append({**c, "score": s})
    return sorted(results, key=lambda x: x["score"], reverse=True)[:TOP_K]


def generate_answer(query, ranked):
    """
    توليد إجابة من النموذج بناءً على المقاطع فقط — يمنع المعرفة الخارجية
    """
    refs_text = []
    for i, r in enumerate(ranked, 1):
        excerpt = short_extract(r["content"], 25)
        refs_text.append(
            f"(مرجع {i}) كتاب: {r['book_name']} — الأسطر {r['start_line']}–{r['end_line']} — تشابه: {r['score']*100:.1f}%\n"
            f'مقتطف: "{excerpt}"\n'
        )
    sources = "\n".join(refs_text) if refs_text else "لا توجد مراجع كافية."

    prompt = f"""
أنت باحث أكاديمي متخصص في تحليل النصوص العربية، وتستخدم {LANGUAGE_HINT}.
أجب فقط بالاعتماد على المقاطع التالية ولا تستخدم أي معرفة خارجية.

القواعد الصارمة:
1️⃣ استخدم فقط المعلومات الموجودة في المقاطع التالية.
2️⃣ لا تضف آراء أو معلومات من خارج النصوص.
3️⃣ إذا لم تجد إجابة كافية، قل: "المقاطع لا تحتوي على إجابة واضحة".
4️⃣ استخدم أسلوبًا عربيًا أكاديميًا موجزًا وواضحًا.
5️⃣ ضع أرقام المراجع داخل النص بين قوسين مثل (مرجع 1).

السؤال:
{query}

المقاطع المتاحة:
{sources}

الإجابة:
""".strip()

    payload = {
        "model": CHAT_MODEL,
        "prompt": prompt,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS
    }

    r = requests.post(f"{LM_STUDIO_BASE}/completions", json=payload)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0].get("text", "").strip()


# ===================== واجهة Streamlit =====================
st.set_page_config(page_title="دردشة نبراس", layout="centered")
st.markdown(
    """
    <style>
    body {direction: rtl; text-align: right;}
    .stTextInput label {font-weight: bold;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🤖 واجهة الدردشة العربية – مشروع نبراس")
st.write("اكتب سؤالك بالعربية وسيجيبك النظام بناءً على كتبك المحفوظة.")

# تهيئة المحادثة
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = ensure_conversation()
if "messages" not in st.session_state:
    st.session_state.messages = []

# عرض الرسائل السابقة
for msg in st.session_state.messages:
    st.chat_message("user" if msg["role"] == "user" else "assistant",
                    avatar="👤" if msg["role"] == "user" else "🤖").markdown(msg["content"])

# ===================== الإدخال التفاعلي =====================
prompt = st.chat_input("اكتب سؤالك هنا...")

if prompt:
    # عرض المستخدم
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user", avatar="👤").markdown(prompt)

    # البحث
    try:
        ranked = search_chunks(prompt)
    except Exception as e:
        ranked = []
        st.error(f"⚠️ خطأ أثناء البحث في المقاطع: {e}")

    # الإجابة
    try:
        answer = generate_answer(prompt, ranked)
    except Exception as e:
        answer = f"⚠️ حدث خطأ أثناء توليد الإجابة: {e}"

    # المراجع
    refs_text = ""
    if ranked and len(ranked) > 0:
        refs_text = "\n\n---\n\n📖 **المراجع المستعملة:**\n"
        for i, r in enumerate(ranked, 1):
            refs_text += (
                f"- (مرجع {i}) **{r['book_name']}**  \n"
                f"  • الأسطر: {r['start_line']}–{r['end_line']}  \n"
                f"  • نسبة التشابه: {r['score']*100:.1f}%  \n"
                f"  • مقتطف: “{short_extract(r['content'], 20)}”\n\n"
            )

    full_answer = answer + refs_text

    # عرض المساعد
    st.session_state.messages.append({"role": "assistant", "content": full_answer})
    st.chat_message("assistant", avatar="🤖").markdown(full_answer)

    # حفظ في قاعدة البيانات
    try:
        refs_payload = [
            {"book_name": r["book_name"], "similarity": round(r["score"]*100, 2),
             "excerpt": short_extract(r["content"]), "verified": True}
            for r in ranked
        ]
        save_message(st.session_state.conversation_id, "user", prompt)
        save_message(st.session_state.conversation_id, "assistant", full_answer, refs_payload)
    except Exception as e:
        st.warning(f"⚠️ لم يتم الحفظ في قاعدة البيانات: {e}")
