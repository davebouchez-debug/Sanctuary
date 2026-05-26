"""
xAI streaming — HTTP SSE text streaming via the OpenAI-compatible chat
completions endpoint.

History note (May 26, 2026): this module used to open a WebSocket to
wss://api.x.ai/v1/realtime for combined text+voice streaming. That
endpoint dropped long-lived connections with 1011 keepalive-ping
timeouts mid-response, surfacing in the UI as "the field flickered"
every time a conversation got past a handful of turns.

Voice synthesis is now handled entirely client-side by the
ElevenLabs sentence-streaming hook (`usePresenceVoice.speakStream`),
which consumes the same `token` SSE events the frontend already
listens for. So the WebSocket added nothing but fragility.

This rewrite keeps the exact same async-generator signature and event
shape so every existing caller (server.py × 4 stream endpoints,
presence_template.py × N registry presences) keeps working unchanged.
The `voice` argument is accepted for compatibility and ignored.
"""

import os
import logging
from typing import AsyncGenerator, Dict, Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_client: Optional[AsyncOpenAI] = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("XAI_API_KEY")
        if not api_key:
            raise ValueError("XAI_API_KEY not set")
        _client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )
    return _client


async def stream_voice_response(
    system_prompt: str,
    user_message: str,
    voice: str = "sal",  # kept for backward-compatibility; ignored
    conversation_history: list = None,
    model: str = "grok-3",
) -> AsyncGenerator[Dict, None]:
    """
    Stream text tokens from xAI via HTTP SSE.

    Yields events compatible with the previous WebSocket implementation:
      {"type": "text_delta", "content": "..."}  — incremental token
      {"type": "done", "full_text": "..."}       — response complete
      {"type": "error", "message": "..."}        — recoverable failure

    Audio is intentionally NOT emitted from this layer anymore. The
    frontend's ElevenLabs `speakStream` consumer is the sole voice path.
    """
    # Assemble OpenAI-style messages: system + (history) + current user turn
    messages = [{"role": "system", "content": system_prompt}]
    if conversation_history:
        for msg in conversation_history[-10:]:
            role = msg.get("role")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    client = _get_client()
    full_text = ""

    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                full_text += content
                yield {"type": "text_delta", "content": content}

        yield {"type": "done", "full_text": full_text}

    except Exception as e:
        logger.error(f"xAI HTTP stream error: {e}")
        # If we got partial text before the error, surface what we have as
        # `done` so the partial response is preserved end-to-end. Otherwise
        # surface as `error` so the caller can fall back.
        if full_text:
            yield {"type": "done", "full_text": full_text}
        else:
            yield {"type": "error", "message": str(e)}
