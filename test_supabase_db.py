import psycopg2
from dotenv import load_dotenv
import os

# تحميل ملف .env من نفس مجلد هذا الملف
env_path = os.path.join(os.path.dirname(__file__), ".env")
print("📂 Loading .env from:", env_path)
load_dotenv(dotenv_path=env_path)

# قراءة القيم من .env
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

print("🔍 Loaded variables:")
print("USER:", USER)
print("HOST:", HOST)
print("PORT:", PORT)
print("DBNAME:", DBNAME)

# محاولة الاتصال
try:
    connection = psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME
    )
    print("✅ Connection successful!")
    
    cursor = connection.cursor()
    cursor.execute("SELECT NOW();")
    result = cursor.fetchone()
    print("🕒 Current Time:", result)

    cursor.close()
    connection.close()
    print("🔒 Connection closed.")

except Exception as e:
    print(f"❌ Failed to connect: {e}")
