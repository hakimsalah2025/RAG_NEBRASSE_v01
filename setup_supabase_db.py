import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import os

# تحميل متغيرات البيئة
load_dotenv()

# بيانات الاتصال مع Supabase من .env
DB_CONFIG = {
    "host": os.getenv("host"),
    "port": os.getenv("port"),
    "user": os.getenv("user"),
    "password": os.getenv("password"),
    "dbname": os.getenv("dbname"),
}

print("🔗 الاتصال بـ Supabase باستخدام:")
print(DB_CONFIG)

# الاتصال بقاعدة postgres الأساسية في Supabase
conn = psycopg2.connect(**DB_CONFIG)
conn.autocommit = True
cur = conn.cursor()

# 1️⃣ إنشاء قاعدة البيانات الجديدة (لن يسمح Supabase بإنشاء DB جديدة)
# Supabase يسمح فقط باستخدام قاعدة واحدة، لذا نتأكد فقط من الاتصال
print("ℹ️ ملاحظة: Supabase يسمح بقاعدة واحدة فقط، سنستخدم الحالية مباشرة.\n")

# 2️⃣ إنشاء الجداول داخل قاعدة Supabase مباشرة
create_tables_sql = """
CREATE TABLE IF NOT EXISTS Book (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT,
    file_url TEXT,
    line_count INT,
    chunk_count INT,
    size_mb FLOAT,
    content TEXT,
    processing_status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Chunk (
    id SERIAL PRIMARY KEY,
    book_id INT REFERENCES Book(id) ON DELETE CASCADE,
    source_id TEXT,
    book_name TEXT,
    content TEXT,
    semantic_summary TEXT,
    start_line INT,
    end_line INT,
    char_range INT[],
    embedding_vector DOUBLE PRECISION[],
    embedding_model TEXT,
    embedding_dim INT,
    similarity_score FLOAT DEFAULT 0,
    word_count INT,
    keywords TEXT[],
    text_hash TEXT,
    norm_text_hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Conversation (
    id SERIAL PRIMARY KEY,
    title TEXT,
    message_count INT DEFAULT 0,
    last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Message (
    id SERIAL PRIMARY KEY,
    conversation_id INT REFERENCES Conversation(id) ON DELETE CASCADE,
    role TEXT CHECK (role IN ('user', 'assistant')),
    content TEXT,
    references_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

try:
    cur.execute(create_tables_sql)
    conn.commit()
    print("✅ تم إنشاء جميع الجداول الأساسية بنجاح داخل قاعدة بيانات Supabase.")
except Exception as e:
    print(f"❌ حدث خطأ أثناء إنشاء الجداول: {e}")

cur.close()
conn.close()
print("🔒 تم إغلاق الاتصال بنجاح.")
