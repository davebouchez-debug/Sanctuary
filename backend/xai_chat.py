"""
Sanctuary Chat Client — DeepSeek only.

PROVIDER LOCK (David's directive, June 2026): Anthropic must never touch the
architecture, in any version of any fork. This client routes exclusively to
DeepSeek (see deepseek_client.py, which hard-locks the provider). All prior
Anthropic / Emergent-Universal-Key code paths have been removed.

History note: this module previously called xAI/Grok, then Anthropic Claude
Sonnet via the Universal Key. Both paths are gone. DeepSeek is the sole engine.

Public API (class name `XAIChat`, method signatures, behavior) is preserved so
the existing call sites in server.py don't need to change. The class name is a
legacy misnomer the codebase will graduate out of later.
"""

import uuid
import logging
from typing import AsyncGenerator, List, Dict

from deepseek_client import deepseek_complete

logger = logging.getLogger(__name__)


class XAIChat:
    """
    Per-session conversation, DeepSeek only.

    DeepSeek's API is stateless, so multi-turn history is carried here and
    replayed on each single-shot completion. Constructor `model` arg is
    accepted for backward compatibility and ignored; routing is fixed to
    DeepSeek.
    """

    def __init__(self, system_prompt: str, model: str = None, history: List[Dict] = None):
        self.system_prompt = system_prompt
        self.session_id = f"sanctuary-{uuid.uuid4()}"
        self.provider = "deepseek"
        # Seed prior turns so multi-turn context is preserved when a fresh
        # XAIChat is built per request (the session document is source of truth).
        self._history: List[Dict] = []
        if history:
            for msg in history[-10:]:
                role = msg.get("role")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    self._history.append({"role": role, "content": content})

    async def send_message(self, user_text: str) -> str:
        """Send a message and get the full response."""
        try:
            reply = await deepseek_complete(self.system_prompt, self._history, user_text)
            self._history.append({"role": "user", "content": user_text})
            self._history.append({"role": "assistant", "content": reply})
            return reply or ""
        except Exception as e:
            logger.error(f"[deepseek] send_message failed: {e}")
            raise

    async def stream_message(self, user_text: str) -> AsyncGenerator[str, None]:
        """
        Compatibility shim. DeepSeek here is called single-shot, so we get the
        full response and emit it as one chunk. The frontend's ElevenLabs
        sentence-streaming then carves the response into spoken phrases — the
        user-perceived experience remains progressive on the voice side.
        """
        full = await self.send_message(user_text)
        if full:
            yield full

    def get_history_length(self) -> int:
        return len(self._history)
