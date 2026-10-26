"""Provider-agnostic structured output: every agent gets back a validated Pydantic model.

Providers (set LLM_PROVIDER in .env):
  groq        free tier, fast, OpenAI-compatible
  openrouter  many models incl. free ones (":free" suffix), OpenAI-compatible
  ollama      local models, OpenAI-compatible
  anthropic   Claude via the native SDK (supports prompt caching)
"""

import json
import re
from functools import cache
from typing import Any

from pydantic import BaseModel, ValidationError
from app.config import settings

OPENAI_COMPATIBLE = {
    "groq": ("https://api.groq.com/openai/v1", "groq_api_key"),
    "openrouter": ("https://openrouter.ai/api/v1", "openrouter_api_key"),
    "ollama": (None, None),  # base URL from settings.ollama_base_url, no key needed
}

class LLMError(RuntimeError):
    pass

def structured_call[T: BaseModel](
    *,
    model: str,
    system: str,
    spec_text: str,
    instruction: str,
    output: type[T],
    tool_name: str = "submit",
    max_tokens: int = 8000,
    max_attempts: int = 2,
) -> T:
    """Ask the model to call one tool shaped like `output`; validate, and retry once with the error."""
    schema = inline_refs(output.model_json_schema())
    user_text = f"{spec_text}\n\n{instruction}"
    error_note = ""
    
    for attempt in range(1, max_attempts + 1):
        prompt = user_text + error_note
        if settings.llm_provider == "anthropic":
            raw = _call_anthropic(model, system, spec_text, instruction + error_note, schema, tool_name, output.__name__, max_tokens)
        
        else:
            raw = _call_openai_compatible(model, system, prompt, schema, tool_name, output.__name__, max_tokens)
            
        try:
            return output.model_validate(raw)
        except ValidationError as exc:
            if attempt == max_attempts:
                raise LLMError(f"{model} returned invalid {output.__name__}: {exc}") from exc
            # Feed the validation error back so the model can fix its own output.
            error_note = (
                f"\n\nYour previous answer failed validation:\n{exc}\n"
                f"Call `{tool_name}` again with corrected arguments."
            )
    raise LLMError("unreachable")

# --- OpenAI-compatible providers (Groq, OpenRouter, Ollama) -------------------------------

@cache
def _openai_client():
    from openai import OpenAI

    provider = settings.llm_provider
    if provider not in OPENAI_COMPATIBLE:
        raise LLMError(f"Unknown LLM_PROVIDER '{provider}'")
    base_url, key_field = OPENAI_COMPATIBLE[provider]
    if provider == "ollama":
        return OpenAI(base_url=settings.ollama_base_url, api_key="ollama", max_retries=5)
    api_key = getattr(settings, key_field)
    if not api_key:
        raise LLMError(f"{key_field.upper()} is not set in .env")
    headers = {"X-Title": "Specwright"} if provider == "openrouter" else None
    # max_retries backs off automatically on 429s from free-tier rate limits.
    return OpenAI(base_url=base_url, api_key=api_key, default_headers=headers, max_retries=5)


def _call_openai_compatible(model, system, prompt, schema, tool_name, type_name, max_tokens):
    response = _openai_client().chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        temperature=0,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        tools=[{
            "type": "function",
            "function": {
                "name": tool_name,
                "description": f"Submit the result as {type_name}.",
                "parameters": schema,
            },
        }],
        tool_choice={"type": "function", "function": {"name": tool_name}},
    )
    message = response.choices[0].message
    call = message.tool_calls[0] if message.tool_calls else None
    if call and call.type == "function":
        return json.loads(call.function.arguments)
    # Some free/local models ignore tool_choice and answer in text; try to recover the JSON.
    return extract_json(message.content or "")
            
            
            
# --- Anthropic (native SDK, with prompt caching) ------------------------------------------
@cache
def _anthropic_client():
    from anthropic import Anthropic
    
    if not settings.anthropic_api_key:
        raise LLMError("ANTHROPIC_API_KEY is not set in .env")
    return Anthropic(api_key=settings.anthropic_api_key)

def _call_anthropic(model, system, spec_text, instruction, schema, tool_name, type_name,
                    max_tokens):
    response = _anthropic_client().messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        tools=[{"name": tool_name, "description": f"Submit the result as {type_name}.",
                "input_schema": schema}],
        tool_choice={"type": "tool", "name": tool_name},
        messages=[{
            "role": "user",
            "content": [
                # Shared prefix across stages -> cached once per run.
                {"type": "text", "text": spec_text, "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": instruction},
            ],
        }],
    )
    block = next(b for b in response.content if b.type == "tool_use")
    return block.input

# --- Helpers -------------------------------------------------------------------------------

def inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Replace Pydantic's $ref/$defs with inline definitions; some providers reject $ref."""
    defs = schema.get("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                return resolve(defs[node["$ref"].split("/")[-1]])
            return {k: resolve(v) for k, v in node.items() if k != "$defs"}
        if isinstance(node, list):
            return [resolve(v) for v in node]
        return node

    return resolve(schema)


def extract_json(text: str) -> Any:
    """Pull the first JSON object out of a text reply (handles ```json fences)."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text[text.find("{"): text.rfind("}") + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Model did not return a tool call or JSON: {text[:200]!r}") from exc