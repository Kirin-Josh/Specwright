# Run from apps/api as a module so `app` is importable: python -m app.playground
from anthropic import Anthropic
from app.config import settings

client = Anthropic(api_key=settings.anthropic_api_key)

response = client.messages.create(
    model=settings.specwright_model_extract,
    max_tokens=1000,
    system="You are a senior tech lead.",
    messages=[{"role": "user", "content": "List the requirements in this spec: ..."}],
)

for block in response.content:
    if block.type == "text":
        print(block.text)
print(response.usage)