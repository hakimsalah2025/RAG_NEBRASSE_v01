import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("host"),
    port=os.getenv("port"),
    user=os.getenv("user"),
    password=os.getenv("password"),
    dbname=os.getenv("dbname")
)
cur = conn.cursor()

try:
    # إضافة كتاب تجريبي
    cur.execute("""
        INSERT INTO Book (name, type, file_url, line_count, chunk_count, size_mb, content, processing_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, ("اللغة والهوية", "نص أكاديمي", "none", 120, 10, 0.45, "نص تجريبي حول العلاقة بين اللغة والهوية.", "ready"))

    book_id = cur.fetchone()[0]
    print(f"✅ تمت إضافة كتاب تجريبي (ID={book_id})")

    # إضافة محادثة بسيطة
    cur.execute("""
        INSERT INTO Conversation (title, message_count)
        VALUES (%s, %s)
        RETURNING id;
    """, ("محادثة تجريبية", 0))

    conv_id = cur.fetchone()[0]
    print(f"✅ تمت إضافة محادثة تجريبية (ID={conv_id})")

    conn.commit()

except Exception as e:
    print("❌ خطأ أثناء الإدخال:", e)

finally:
    cur.close()
    conn.close()
    print("🔒 تم إغلاق الاتصال.")
