import psycopg2
from psycopg2 import sql

# إعداد معلومات الاتصال
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,                     # ✅ المنفذ المحدد
    "user": "postgres",
    "password": "13@04@1971",
    "dbname": "postgres"
}

NEW_DB_NAME = "nebras_rag"

# الاتصال بقاعدة postgres الافتراضية
conn = psycopg2.connect(**DB_CONFIG)
conn.autocommit = True
cur = conn.cursor()

# 1. إنشاء قاعدة البيانات الجديدة إذا لم تكن موجودة
cur.execute(sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s;"), [NEW_DB_NAME])
exists = cur.fetchone()
if not exists:
    cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(NEW_DB_NAME)))
    print(f"✅ تم إنشاء قاعدة البيانات '{NEW_DB_NAME}' بنجاح.")
else:
    print(f"ℹ️ قاعدة البيانات '{NEW_DB_NAME}' موجودة مسبقًا.")

cur.close()
conn.close()

# 2. الاتصال بقاعدة nebras_rag الجديدة
conn2 = psycopg2.connect(
    host="localhost",
    port=5432,                       # ✅ نفس المنفذ
    user="postgres",
    password="13@04@1971",
    dbname=NEW_DB_NAME
)
cur2 = conn2.cursor()

# 3. إنشاء الجداول الأساسية
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

cur2.execute(create_tables_sql)
conn2.commit()

print("✅ تم إنشاء جميع الجداول الأساسية بنجاح داخل قاعدة البيانات 'nebras_rag'.")

cur2.close()
conn2.close()
