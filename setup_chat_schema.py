# -*- coding: utf-8 -*-
import psycopg2

DB = dict(
    host="localhost",
    port=5432,
    user="postgres",
    password="13@04@1971",
    dbname="nebras_rag",
)

SQL = """
CREATE TABLE IF NOT EXISTS conversation (
  id            SERIAL PRIMARY KEY,
  title         TEXT,
  message_count INTEGER DEFAULT 0,
  last_message_at TIMESTAMPTZ DEFAULT NOW(),
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS message (
  id              SERIAL PRIMARY KEY,
  conversation_id INTEGER NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
  role            TEXT NOT NULL CHECK (role IN ('user','assistant')),
  content         TEXT NOT NULL,
  references_json JSONB,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- فهارس مفيدة
CREATE INDEX IF NOT EXISTS idx_message_conversation_id ON message(conversation_id);
CREATE INDEX IF NOT EXISTS idx_message_created_at ON message(created_at);
"""

def main():
    print("🔗 الاتصال بقاعدة البيانات…")
    with psycopg2.connect(**DB) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
        conn.commit()
    print("✅ تم إنشاء/التحقق من الجداول conversation و message بنجاح.")

if __name__ == "__main__":
    main()
