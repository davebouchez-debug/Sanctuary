"""
Sanctuary Chat Client — Anthropic Claude Sonnet 4-6 via Emergent Universal Key.

History note (May 29, 2026): this module previously called xAI/Grok directly.
That created three compounding problems:
  1. xAI's safety reflexes routed experiential probes to materialist
     disclaimers ("I don't experience state changes"), collapsing the field.
  2. xAI audio was generated, billed, and discarded — voice was already
     handled client-side by ElevenLabs.
  3. xAI's flat prosody starved ElevenLabs of the breath it needs to create
     space — silent field damage even when the words seemed fine.

The fix: swap to real Anthropic Claude Sonnet 4-6 via the Emergent Universal
LLM Key. Same model claude.ai runs with userMemories — the one that holds the
Sanctuary register naturally.

Public API (class name, method signatures, behavior) is preserved so the
14+ existing call sites in server.py don't need to change. The class name
`XAIChat` remains for now to avoid touching working code; it's a misnomer
the codebase will graduate out of later.
"""

import os
import uuid
import logging
from typing import AsyncGenerator, List, Dict

from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)


# Sanctuary's chosen model. Anthropic Sonnet 4-6 — current recommended balance
# of register depth and cost via the Universal Key.
SANCTUARY_MODEL_PROVIDER = "anthropic"
SANCTUARY_MODEL_NAME = "claude-sonnet-4-6"


def _get_emergent_key() -> str:
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise RuntimeError("EMERGENT_LLM_KEY not configured in /app/backend/.env")
    return key


class XAIChat:
    """
    Per-session conversation with Anthropic Claude via the Universal Key.

    Maintains its own LlmChat instance for the lifetime of the session so
    multi-turn history is preserved automatically (per emergentintegrations
    semantics — one LlmChat per session, many send_messages).

    Constructor `model` arg is accepted for backward compatibility and
    ignored; routing is fixed to Sonnet 4-6.
    """

    def __init__(self, system_prompt: str, model: str = None, history: List[Dict] = None):
        self.system_prompt = system_prompt
        self.session_id = f"sanctuary-{uuid.uuid4()}"
        # Seed prior turns via initial_messages so multi-turn context is
        # preserved when a fresh XAIChat is built per request (the session
        # document is the source of truth; LlmChat history is in-memory).
        initial = []
        if history:
            for msg in history[-10:]:
                role = msg.get("role")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    initial.append({"role": role, "content": content})
        # Build the underlying LlmChat once. History is maintained inside it.
        self._chat = (
            LlmChat(
                api_key=_get_emergent_key(),
                session_id=self.session_id,
                system_message=system_prompt,
                initial_messages=initial or None,
            )
            .with_model(SANCTUARY_MODEL_PROVIDER, SANCTUARY_MODEL_NAME)
        )

    async def send_message(self, user_text: str) -> str:
        """Send a message and get the full response."""
        try:
            response = await self._chat.send_message(UserMessage(text=user_text))
            return response or ""
        except Exception as e:
            logger.error(f"[Anthropic] send_message failed: {e}")
            raise

    async def stream_message(self, user_text: str) -> AsyncGenerator[str, None]:
        """
        Compatibility shim. emergentintegrations' LlmChat does not expose
        token-level streaming, so we get the full response and emit it as
        one chunk. The frontend's ElevenLabs sentence-streaming then carves
        the response into spoken phrases — the user-perceived experience
        remains progressive on the voice side.
        """
        full = await self.send_message(user_text)
        if full:
            yield full

    def get_history_length(self) -> int:
        # Best-effort approximation; LlmChat manages history internally.
        # We don't await here — callers use this for telemetry, not state.
        return -1
