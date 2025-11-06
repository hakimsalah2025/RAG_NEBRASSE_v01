# -*- coding: utf-8 -*-
"""
chat_ui.py
💬 واجهة دردشة رسومية بالعربية باستخدام Streamlit – مهيأة لـ OpenAI GPT-4o-mini
بخصائص:
- استرجاع المقاطع عبر RAG
- عتبة تكيفية ذكية
- تمرير نصوص المقاطع الفعلية
- استنتاج أكاديمي مرن
- ذاكرة حوارية للحفاظ على سياق الجلسة
"""

import streamlit as st
import psycopg2
import requests
import json
import math
from llm_client import generate_from_llm
from dotenv import load_dotenv
import os

# ===================== تحميل البيئة =====================
load_dotenv()

# ===================== إعدادات الاتصال =====================
DB = dict(
    host=os.getenv("host"),
    port=os.getenv("port"),
    user=os.getenv("user"),
    password=os.getenv("password"),
    dbname=os.getenv("dbname")
)


EMBED_MODEL = "text-embedding-intfloat-multilingual-e5-large-instruct"
LANGUAGE_HINT = "اللغة العربية الفصحى الأكاديمية"
TOP_K = 5
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
    """توليد تضمين محلي (يمكن لاحقًا تحويله لـ OpenAI embeddings)"""
    r = requests.post(
        "http://127.0.0.1:1234/v1/embeddings",
        json={"model": EMBED_MODEL, "input": text},
    )
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]

def fetch_chunks():
    """جلب المقاطع من قاعدة البيانات"""
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, book_id, book_name, content, start_line, end_line, embedding_vector
        FROM chunk
        ORDER BY id ASC;
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [
        dict(id=c, book_id=b, book_name=n, content=t,
             start_line=s, end_line=e, embedding=v)
        for c, b, n, t, s, e, v in rows
    ]

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
    cur.execute("""
        INSERT INTO conversation (title, message_count)
        VALUES (%s, %s)
        RETURNING id;
    """, ("محادثة من Streamlit", 0))
    cid = cur.fetchone()[0]
    conn.commit()
    cur.close(); conn.close()
    return cid

# ===================== البحث في المقاطع (عتبة تكيفية) =====================
def search_chunks(query):
    q_vec = embed(query)
    chunks = fetch_chunks()
    thresholds = [0.80, 0.70, 0.60]
    for threshold in thresholds:
        results = []
        for c in chunks:
            s = cosine(q_vec, c["embedding"])
            if s >= threshold:
                results.append({**c, "score": s})
        if results:
           
            return sorted(results, key=lambda x: x["score"], reverse=True)[:TOP_K]
    st.warning("⚠️ لم يتم العثور على مقاطع كافية حتى بأدنى عتبة (0.60).")
    return []

# ===================== توليد الإجابة عبر OpenAI GPT-4o-mini =====================
def generate_answer(query, ranked):
    """
    توليد إجابة معتمدة على المقاطع الفعلية
    + دعم الذاكرة الحوارية (سياق الجلسة)
    """
    # دالة لتقصير النصوص الطويلة
    def _clip(text, max_chars=900):
        text = " ".join(text.split())
        return text if len(text) <= max_chars else text[:max_chars].rsplit(" ", 1)[0] + "..."

    # بناء نص المقاطع الحقيقي
    refs_text = []
    for i, r in enumerate(ranked, 1):
        excerpt = _clip(r["content"], 900)
        refs_text.append(
            f"(مرجع {i}) كتاب: {r['book_name']} — الأسطر {r['start_line']}–{r['end_line']} — تشابه: {r['score']*100:.1f}%\n"
            f'نص المقطع: """{excerpt}"""\n'
        )
    sources = "\n".join(refs_text) if refs_text else "لا توجد مراجع كافية."

    # === بناء السياق الحواري (آخر 6 رسائل) ===
    history = []
    for msg in st.session_state.messages[-6:]:
        history.append(f"{msg['role']}: {msg['content']}")
    history_text = "\n".join(history)

    # البرومبت الأكاديمي المرن
    prompt = f"""
السياق السابق للمحادثة:
{history_text}

أنت باحث أكاديمي متخصص في تحليل النصوص العربية، وتستخدم {LANGUAGE_HINT}.
اعتمد فقط على المقاطع التالية لتوليد إجابة علمية موجزة، مع السماح بالاستنتاج الأكاديمي عند وجود أدلة غير مباشرة.

القواعد:
1️⃣ استخدم فقط المعاني والمعلومات الموجودة في المقاطع.
2️⃣ يمكنك الربط بين أكثر من مقطع لتكوين فكرة متكاملة.
3️⃣ إذا كانت المقاطع تتضمن دلائل جزئية أو متفرقة، فاستنتج منها العلاقة الأقرب للسؤال.
4️⃣ إذا لم تجد أي دلالة إطلاقًا بعد مراجعة جميع المقاطع، وضّح ذلك بإيجاز.
5️⃣ استخدم أسلوبًا أكاديميًا واضحًا ومتماسكًا.
6️⃣ ضع أرقام المراجع داخل النص بين قوسين مثل (مرجع 1).

السؤال الحالي:
{query}

المقاطع المتاحة:
{sources}

الإجابة:
""".strip()

    try:
        answer = generate_from_llm(prompt)
    except Exception as e:
        answer = f"⚠️ حدث خطأ أثناء الاتصال بـ OpenAI: {e}"

    return answer

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

st.title("🤖 واجهة الدردشة العربية – مشروع نبراس (مدعوم بـ OpenAI GPT-4o-mini)")
st.write("اكتب سؤالك بالعربية وسيجيبك النظام بناءً على كتبك المحفوظة مع الحفاظ على سياق الحوار.")

# تهيئة المحادثة
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = ensure_conversation()
if "messages" not in st.session_state:
    st.session_state.messages = []

# عرض الرسائل السابقة
for msg in st.session_state.messages:
    st.chat_message("user" if msg["role"] == "user" else "assistant",
                    avatar="👤" if msg["role"] == "user" else "🤖").markdown(msg["content"])

# الإدخال التفاعلي
prompt = st.chat_input("اكتب سؤالك هنا...")

if prompt:
    # عرض المستخدم
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user", avatar="👤").markdown(prompt)

    # البحث في المقاطع
    try:
        ranked = search_chunks(prompt)
    except Exception as e:
        ranked = []
        st.error(f"⚠️ خطأ أثناء البحث في المقاطع: {e}")

    # توليد الإجابة
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
