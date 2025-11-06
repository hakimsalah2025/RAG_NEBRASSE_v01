# -*- coding: utf-8 -*-
"""
ingest_books_supabase.py
📚 إدخال الكتب إلى قاعدة Supabase السحابية
"""

import os
import json
import math
import psycopg2
import requests
from tqdm import tqdm
from dotenv import load_dotenv

# ===================== إعدادات النظام =====================
load_dotenv()

DB = dict(
    host=os.getenv("host"),
    port=os.getenv("port"),
    user=os.getenv("user"),
    password=os.getenv("password"),
    dbname=os.getenv("dbname"),
)

# يمكن لاحقًا استبدال هذا النموذج بموديل OpenAI مباشرة
EMBED_MODEL = "text-embedding-intfloat-multilingual-e5-large-instruct"
LM_STUDIO_BASE = "http://127.0.0.1:1234/v1"  # إذا لم تستخدم LM Studio، يمكن تعطيله مؤقتًا

CHUNK_SIZE = 400
OVERLAP = 40  # تداخل 10%
BOOKS_DIR = "./books"  # تأكد من وجود كتب .txt داخله

# ===================== أدوات مساعدة =====================
def connect_db():
    """اتصال بقاعدة Supabase"""
    return psycopg2.connect(**DB)


def normalize_arabic(text):
    """تطبيع النص العربي"""
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي").replace("ة", "ه")
    return " ".join(text.split())


def embed_text(text):
    """توليد تضمين — حاليًا عبر LM Studio (يمكن استبداله لاحقًا بـ OpenAI)"""
    try:
        r = requests.post(f"{LM_STUDIO_BASE}/embeddings",
                          json={"model": EMBED_MODEL, "input": text})
        r.raise_for_status()
        return r.json()["data"][0]["embedding"]
    except Exception as e:
        print(f"⚠️ خطأ أثناء إنشاء التضمين: {e}")
        # إذا لم يتوفر LM Studio، يمكنك إرجاع قائمة فارغة مؤقتًا
        return [0.0] * 768


def chunk_text(content):
    """تجزئة النص إلى مقاطع مع تحديد الأسطر"""
    lines = [l.strip() for l in content.split("\n") if l.strip()]
    line_count = len(lines)
    words = content.split()
    total_words = len(words)

    chunks = []
    step = CHUNK_SIZE - OVERLAP

    for i in range(0, total_words, step):
        chunk_words = words[i:i + CHUNK_SIZE]
        chunk_text = " ".join(chunk_words)

        # تحديد نطاق الأسطر التقريبي بناءً على النسبة
        start_ratio = i / total_words
        end_ratio = min((i + CHUNK_SIZE) / total_words, 1)
        start_line = int(start_ratio * line_count) + 1
        end_line = int(end_ratio * line_count)

        chunks.append({
            "content": chunk_text,
            "start_line": start_line,
            "end_line": end_line,
        })

    return chunks


def insert_book(conn, name, content, chunk_count, line_count):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO book (name, type, file_url, line_count, chunk_count, size_mb, content, processing_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (name, 'text/plain', '', line_count, chunk_count, 0.0, content, 'completed'))
    book_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    return book_id


def insert_chunk(conn, book_id, book_name, content, start_line, end_line, embedding):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO chunk (book_id, book_name, content, start_line, end_line, embedding_vector, embedding_model, embedding_dim)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """, (book_id, book_name, content, start_line, end_line, embedding, EMBED_MODEL, len(embedding)))
    conn.commit()
    cur.close()


# ===================== المعالجة =====================
def ingest_book(file_path):
    """معالجة كتاب واحد"""
    book_name = os.path.basename(file_path)
    print(f"\n📘 معالجة الكتاب: {book_name}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    norm_content = normalize_arabic(content)
    chunks = chunk_text(norm_content)

    conn = connect_db()
    book_id = insert_book(conn, book_name, norm_content, len(chunks), len(content.split("\n")))

    print(f"📘 الكتاب يحتوي على {len(chunks)} مقاطع.")
    for c in tqdm(chunks, desc="🔹 معالجة المقاطع"):
        emb = embed_text(c["content"])
        insert_chunk(conn, book_id, book_name, c["content"], c["start_line"], c["end_line"], emb)

    conn.close()
    print(f"✅ تم إدخال الكتاب '{book_name}' بنجاح إلى Supabase.")


def main():
    files = [f for f in os.listdir(BOOKS_DIR) if f.endswith(".txt")]
    if not files:
        print("❌ لم يتم العثور على كتب في المجلد ./books")
        return

    for f in files:
        ingest_book(os.path.join(BOOKS_DIR, f))


if __name__ == "__main__":
    main()
