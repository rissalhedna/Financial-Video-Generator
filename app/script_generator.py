from __future__ import annotations

import json
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from openai import OpenAI

from .config import get_settings
from .models import InputData, Script
from .prompt_templates import SYSTEM_PROMPT, build_user_prompt


def _client() -> OpenAI:
    settings = get_settings()
    return OpenAI(api_key=settings.openai_api_key, timeout=60.0)

@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=8),
    retry=retry_if_exception_type(Exception),
)
def generate_script(input_data: InputData, use_ai_speech_control: bool = False) -> Script:
    """
    Call LLM (configured in settings) to generate a short-form financial script in JSON, then validate with Pydantic.
    
    Args:
        input_data: Input data with topic, facts, news, etc.
        use_ai_speech_control: If True, GPT will provide emphasis_words and pause_after_ms for AI-driven speech control
    """
    settings = get_settings()
    client = _client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(input_data, use_ai_speech_control)},
    ]
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.8,
    )
    content = resp.choices[0].message.content or "{}"
    data: Any = json.loads(content)
    script = Script.model_validate(data)

    # Guardrail: ensure disclaimer present
    if not script.disclaimer.lower().strip():
        script.disclaimer = "Educational only, not investment advice."
    return script


