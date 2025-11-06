from dotenv import load_dotenv
import os

load_dotenv()  # يحمّل المتغيرات من ملف .env

print("قيمة المفتاح هي:")
print(os.getenv("OPENAI_API_KEY"))

print("\nهل المفتاح موجود؟", bool(os.getenv("OPENAI_API_KEY")))
