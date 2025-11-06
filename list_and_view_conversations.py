# -*- coding: utf-8 -*-
"""
list_and_view_conversations.py
🔹 عرض المحادثات والرسائل المحفوظة في قاعدة البيانات
"""

import psycopg2
from datetime import datetime

# ===================== إعدادات الاتصال =====================
DB = dict(
    host="localhost",
    port=5432,
    user="postgres",
    password="13@04@1971",
    dbname="nebras_rag",
)


# ===================== الدوال =====================
def connect_db():
    return psycopg2.connect(**DB)


def list_conversations():
    """عرض قائمة المحادثات"""
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, message_count, last_message_at, created_at
        FROM conversation
        ORDER BY id DESC;
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()

    if not rows:
        print("⚠️ لا توجد محادثات محفوظة بعد.")
        return []

    print("\n📜 قائمة المحادثات:\n")
    for row in rows:
        cid, title, msg_count, last_at, created = row
        last_str = last_at.strftime("%Y-%m-%d %H:%M") if last_at else "-"
        print(f"🗂️ ID {cid} | {title or '(بدون عنوان)'} | رسائل: {msg_count or 0} | آخر تحديث: {last_str}")
    return rows


def view_conversation(conversation_id):
    """عرض كل الرسائل داخل محادثة معينة"""
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, role, content, references_json, created_at
        FROM message
        WHERE conversation_id = %s
        ORDER BY id ASC;
    """, (conversation_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()

    if not rows:
        print("⚠️ لا توجد رسائل في هذه المحادثة.")
        return

    print(f"\n💬 محتوى المحادثة رقم {conversation_id}:\n")
    for mid, role, content, refs, created in rows:
        stamp = created.strftime("%Y-%m-%d %H:%M")
        prefix = "👤 المستخدم:" if role == "user" else "🤖 المساعد:"
        print(f"{prefix} ({stamp})")
        print(content.strip(), "\n")
        if role == "assistant" and refs:
            print("📖 المراجع:\n", refs, "\n")
        print("─" * 60)


# ===================== التنفيذ =====================
if __name__ == "__main__":
    print("🔍 استعراض المحادثات...\n")
    convs = list_conversations()

    if convs:
        try:
            cid = int(input("\nاكتب رقم المحادثة التي تريد عرضها: "))
            view_conversation(cid)
        except ValueError:
            print("⚠️ رقم غير صالح.")
