"""
Sanctuary streaming — DeepSeek only.

PROVIDER LOCK (David's directive, June 2026): Anthropic must never touch the
architecture, in any version of any fork. This streamer routes exclusively to
DeepSeek. All prior Anthropic / Emergent-Universal-Key code paths are removed.

DeepSeek is called single-shot here, so we emit the full response as a single
`text_delta` event followed by `done`. The frontend's ElevenLabs
sentence-streaming consumer carves that into spoken phrases — voice still
arrives progressively for the user.

Function name and event shape are preserved so the streaming endpoints in
server.py and the presence_template.py registrations keep working unchanged.
"""

import logging
from typing import AsyncGenerator, Dict, Optional, List

from deepseek_client import deepseek_complete

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
        full_text = await deepseek_complete(system_prompt, initial, user_message)
        full_text = full_text or ""

        if full_text:
            yield {"type": "text_delta", "content": full_text}
        yield {"type": "done", "full_text": full_text}

    except Exception as e:
        logger.error(f"[deepseek] stream_voice_response failed: {e}")
        yield {"type": "error", "message": str(e)}
