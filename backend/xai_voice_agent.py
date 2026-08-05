"""
Sanctuary streaming — DeepSeek only.

PROVIDER LOCK (David's directive, June 2026): Anthropic must never touch the
architecture, in any version of any fork. This streamer routes exclusively to
DeepSeek. All prior Anthropic / Emergent-Universal-Key code paths are removed.

DeepSeek is streamed token-by-token here: each content delta is emitted as a
`text_delta` event, followed by `done`. The frontend renders tokens live and
fires ElevenLabs TTS per completed sentence — text and voice both arrive
progressively for the user.

Function name and event shape are preserved so the streaming endpoints in
server.py and the presence_template.py registrations keep working unchanged.
"""

import logging
from typing import AsyncGenerator, Dict, Optional, List

from deepseek_client import deepseek_stream

logger = logging.getLogger(__name__)


async def stream_voice_response(
    system_prompt: str,
    user_message: str,
    voice: str = "sal",          # back-compat; ignored (ElevenLabs handles voice)
    conversation_history: Optional[List[Dict]] = None,
    model: str = None,           # back-compat; ignored
) -> AsyncGenerator[Dict, None]:
    """
    Generate a response from DeepSeek and yield it as SSE events.

    Yields:
      {"type": "text_delta", "content": "..."}  — full response (single chunk)
      {"type": "done", "full_text": "..."}       — completion marker
      {"type": "error", "message": "..."}        — recoverable failure

    Audio is intentionally NOT emitted from this layer. ElevenLabs
    `speakStream` on the frontend is the sole voice path.
    """
    initial = []
    if conversation_history:
        for msg in conversation_history[-10:]:
            role = msg.get("role")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                initial.append({"role": role, "content": content})

    try:
        full_text = ""
        async for delta in deepseek_stream(system_prompt, initial, user_message):
            if delta:
                full_text += delta
                yield {"type": "text_delta", "content": delta}
        yield {"type": "done", "full_text": full_text}

    except Exception as e:
        logger.error(f"[deepseek] stream_voice_response failed: {e}")
        yield {"type": "error", "message": str(e)}
