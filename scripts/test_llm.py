import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL"),
)
resp = client.chat.completions.create(
    model=os.getenv("LLM_MODEL"),
    messages=[{"role": "user", "content": "Скажи привет одним предложением"}],
)
print(resp.choices[0].message.content)
