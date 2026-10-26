# Run from apps/api as a module so `app` is importable: python -m app.playground
import sys

from openai import OpenAI

from app.config import settings

# Windows consoles default to cp1252, which can't print some characters models emit.
sys.stdout.reconfigure(encoding="utf-8")

# Groq exposes an OpenAI-compatible API, so the OpenAI SDK works with Groq's base URL.
client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=settings.groq_api_key)

response = client.chat.completions.create(
    model=settings.specwright_model_extract,
    max_tokens=1000,
    messages=[
        {"role": "system", "content": "You are a senior tech lead."},
        {"role": "user", "content": "List the requirements in this spec: ..."},
    ],
)

print(response.choices[0].message.content)
print(response.usage)
