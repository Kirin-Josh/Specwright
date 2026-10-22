"""Forced-tool-use helper: every agent returns a validated Pydantic model."""

from typing import TypeVar

from anthropic import Anthropic
from pydantic import BaseModel

from app.config import settings

T = TypeVar("T", bound=BaseModel)

client = Anthropic(api_key=settings.anthropic_api_key)


def structured_call(
    *,
    model: str,
    system: str,
    spec_text: str,
    instruction: str,
    output: type[T],
    tool_name: str = "submit",
    max_tokens: int = 16000,
) -> T:
    """Call Claude with the spec as a cached prefix and force one tool call shaped like `output`."""
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        tools=[
            {
                "name": tool_name,
                "description": f"Submit the result as {output.__name__}.",
                "input_schema": output.model_json_schema(),
            }
        ],
        tool_choice={"type": "tool", "name": tool_name},
        messages=[
            {
                "role": "user",
                "content": [
                    # Shared prefix across stages -> cached once per run.
                    {"type": "text", "text": spec_text, "cache_control": {"type": "ephemeral"}},
                    {"type": "text", "text": instruction},
                ],
            }
        ],
    )
    block = next(b for b in response.content if b.type == "tool_use")
    return output.model_validate(block.input)
