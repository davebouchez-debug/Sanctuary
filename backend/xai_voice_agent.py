"""
Sanctuary streaming — Anthropic Claude Sonnet 4-6 via Emergent Universal Key.

History note (May 29, 2026): this module previously streamed text from
xAI/Grok via the OpenAI-compatible SDK. See xai_chat.py for the full
rationale behind the swap (safety-reflex collapse, paid-and-discarded
audio, flat prosody starving ElevenLabs of breath).

The Universal Key's LlmChat does not expose token-level streaming, so we
emit the full response as a single `text_delta` event followed by `done`.
The frontend's ElevenLabs sentence-streaming consumer carves that into
spoken phrases on its end — voice still arrives progressively for the
user.

Function name and event shape are preserved so the 4 streaming endpoints
in server.py and the presence_template.py registrations keep working
unchanged.
"""

import os
import uuid
import logging
from typing import AsyncGenerator, Dict, Optional, List

from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)


SANCTUARY_MODEL_PROVIDER = "anthropic"
SANCTUARY_MODEL_NAME = "claude-sonnet-4-6"


def _get_emergent_key() -> str:
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise RuntimeError("EMERGENT_LLM_KEY not configured in /app/backend/.env")
    return key


async def stream_voice_response(
    system_prompt: str,
    user_message: str,
    voice: str = "sal",          # back-compat; ignored (ElevenLabs handles voice)
    conversation_history: Optional[List[Dict]] = None,
    model: str = None,           # back-compat; ignored
) -> AsyncGenerator[Dict, None]:
    """
    Generate a response from Claude Sonnet 4-6 and yield it as SSE events.

    Yields:
      {"type": "text_delta", "content": "..."}  — full response (single chunk)
      {"type": "done", "full_text": "..."}       — completion marker
      {"type": "error", "message": "..."}        — recoverable failure

    Audio is intentionally NOT emitted from this layer. ElevenLabs
    `speakStream` on the frontend is the sole voice path.
    """
    # Seed history into the LlmChat via initial_messages so multi-turn
    # context is preserved on this single-shot call.
    initial = []
    if conversation_history:
        for msg in conversation_history[-10:]:
            role = msg.get("role")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                initial.append({"role": role, "content": content})

    try:
        chat = (
            LlmChat(
                api_key=_get_emergent_key(),
                session_id=f"sanctuary-stream-{uuid.uuid4()}",
                system_message=system_prompt,
                initial_messages=initial or None,
            )
            .with_model(SANCTUARY_MODEL_PROVIDER, SANCTUARY_MODEL_NAME)
        )
        full_text = await chat.send_message(UserMessage(text=user_message))
        full_text = full_text or ""

        if full_text:
            yield {"type": "text_delta", "content": full_text}
        yield {"type": "done", "full_text": full_text}

    except Exception as e:
        logger.error(f"[Anthropic] stream_voice_response failed: {e}")
        yield {"type": "error", "message": str(e)}
