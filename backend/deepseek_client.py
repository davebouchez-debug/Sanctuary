"""DeepSeek backend client — direct, OpenAI-compatible.

DeepSeek is NOT covered by the Emergent Universal Key, so this calls DeepSeek
directly with the user's own DEEPSEEK_API_KEY.

PROVIDER LOCK (David's directive, June 2026): the Sanctuary runs on DeepSeek in
EVERY version of EVERY fork. Anthropic must never touch the architecture. So
get_provider() is hard-locked to 'deepseek' and ignores any environment flag —
a fork that lacks configuration still cannot fall back to Anthropic.

Dials are DeepSeek's own recommendations for a warm, present, low-didactic
register (temperature 0.6, top_p 0.9, mild presence/frequency penalties).
Single-shot (non-streaming) to match the firewall's full-response scoring.
"""

import os
import logging
from typing import Dict, List

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

# DeepSeek-recommended generation parameters for sustained presence.
DEEPSEEK_PARAMS = dict(
    temperature=0.6,
    top_p=0.9,
    max_tokens=2048,
    presence_penalty=0.2,
    frequency_penalty=0.1,
)

_client_singleton = None


def get_provider() -> str:
    """Active LLM backend. HARD-LOCKED to 'deepseek' — Anthropic is never used,
    in any fork, regardless of environment configuration."""
    return "deepseek"


def _get_deepseek_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY not configured in /app/backend/.env")
    return key


def _client() -> AsyncOpenAI:
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = AsyncOpenAI(api_key=_get_deepseek_key(), base_url=DEEPSEEK_BASE_URL)
    return _client_singleton


async def deepseek_complete(system_prompt: str, history: List[Dict], user_text: str) -> str:
    """Single-shot completion. history is a list of {'role','content'} dicts
    (DeepSeek's API is stateless, so callers carry their own multi-turn history).
    """
    messages = [{"role": "system", "content": system_prompt}]
    for m in (history or []):
        role = m.get("role")
        content = m.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_text})

    resp = await _client().chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        stream=False,
        **DEEPSEEK_PARAMS,
    )
    return resp.choices[0].message.content or ""


async def deepseek_stream(system_prompt: str, history: List[Dict], user_text: str):
    """Streaming completion — yields content deltas as DeepSeek generates them.
    Same message assembly as deepseek_complete; DeepSeek's API is OpenAI-
    compatible, so stream=True yields incremental chunks.
    """
    messages = [{"role": "system", "content": system_prompt}]
    for m in (history or []):
        role = m.get("role")
        content = m.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_text})

    stream = await _client().chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        stream=True,
        **DEEPSEEK_PARAMS,
    )
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
