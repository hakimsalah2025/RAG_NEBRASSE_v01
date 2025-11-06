# config.py
from dotenv import load_dotenv
import os

load_dotenv()  # يقرأ ملف .env
LLM_PROVIDER = "openai"          # مؤقتًا سنستخدم OpenAI
OPENAI_MODEL = "gpt-4o-mini"     # سريع وممتاز للعربية

# تأكيد وجود المفتاح
assert os.getenv("OPENAI_API_KEY"), "يرجى وضع OPENAI_API_KEY داخل ملف .env"
