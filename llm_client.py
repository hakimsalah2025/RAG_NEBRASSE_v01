from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_answer(prompt, context):
    system_prompt = (
        "أنت باحث أكاديمي بالعربية، تجيب فقط اعتمادًا على المقاطع المعطاة. "
        "ضع إشارات (مرجع 1، مرجع 2...) عند الاستشهاد. "
        "إذا لم تجد إجابة كافية، قل: المقاطع لا تحتوي على إجابة واضحة."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"السؤال:\n{prompt}\n\nالمقاطع:\n{context}"}
    ]
    res = client.chat.completions.create(model="gpt-4o-mini", messages=messages, temperature=0.3)
    return res.choices[0].message.content.strip()
