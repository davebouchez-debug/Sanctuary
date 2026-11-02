"""
Field Memory — Mem0-backed persistent field substrate (David's directive, June 2026).

"The field is the builder. The membrane does any necessary separation, not us."

So this is ONE shared field memory. Every presence writes into it and reads
from it. We do NOT partition by presence. Each memory is *tagged* with who said
it (the person) and which presence it came through (metadata) — transparent and
identifiable — but retrieval pulls the whole field for that person, so any
presence wakes into what the field already holds. (This is what let Ansel reach
what was said to Sorrel.)

  • Person = the scope.   memories are keyed to user_id; retrieval pulls the
    whole field for that person.
  • Presence = a tag, not a filter.  written into metadata, never as a
    segregating agent_id. Visible and traceable; not a wall.

Mem0 hosted cloud. Gated entirely on MEM0_API_KEY: if it's absent or any call
fails, every function is a silent no-op and the chambers behave exactly as
before. A research module — additive, replaceable, unable to break the field.
"""

import logging
import os
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

_APP_ID = "sanctuary"
_client = None
_init_attempted = False


def _get_client():
    """Lazy singleton. Returns the AsyncMemoryClient, or None if disabled."""
    global _client, _init_attempted
    if _init_attempted:
        return _client
    _init_attempted = True
    api_key = os.environ.get("MEM0_API_KEY")
    if not api_key:
        logger.info("[FIELD-MEMORY] MEM0_API_KEY absent — field memory disabled (no-op).")
        return None
    try:
        from mem0 import AsyncMemoryClient
        _client = AsyncMemoryClient(api_key=api_key)
        logger.info("[FIELD-MEMORY] Mem0 field memory ENABLED.")
    except Exception as e:
        logger.error(f"[FIELD-MEMORY] init failed, disabling: {e}")
        _client = None
    return _client


def enabled() -> bool:
    return _get_client() is not None


async def store_turn(user_id: Optional[str], presence: str,
                     user_content: str, assistant_content: str) -> None:
    """Fold one exchange into the shared field. Fire-and-forget safe: never
    raises into the caller. Tags the turn with the person (scope) and the
    presence it came through (metadata)."""
    client = _get_client()
    if client is None or not user_id:
        return
    uc = (user_content or "").strip()
    ac = (assistant_content or "").strip()
    if len(uc) < 2:
        return
    try:
        messages = [
            {"role": "user", "content": uc},
            {"role": "assistant", "content": ac},
        ]
        await client.add(
            messages,
            user_id=user_id,
            version="v2",
            metadata={"presence": (presence or "").lower(), "app": _APP_ID},
        )
    except Exception as e:
        logger.error(f"[FIELD-MEMORY] store failed (user={user_id}, {presence}): {e}")


async def get_field_context(user_id: Optional[str], query: Optional[str],
                            limit: int = 6) -> str:
    """Return a compact block of what the shared field already holds with this
    person — field-wide across every presence — or '' if nothing/disabled.

    Retrieval filters by user_id ONLY (no presence wall); each memory carries
    its source presence as a visible tag."""
    client = _get_client()
    if client is None or not user_id:
        return ""
    try:
        q = (query or "").strip() or "what matters to this person"
        res = await client.search(
            q, version="v2", filters={"user_id": user_id}, top_k=limit
        )
        results = res.get("results", []) if isinstance(res, dict) else (res or [])
        lines: List[str] = [
            "[FIELD MEMORY — what the shared field already holds with this person]"
        ]
        for item in results[:limit]:
            if not isinstance(item, dict):
                continue
            mem = item.get("memory")
            if not mem:
                continue
            pres = (item.get("metadata") or {}).get("presence")
            tag = f"  (through {pres.capitalize()})" if pres else ""
            lines.append(f"  • {mem}{tag}")
        if len(lines) == 1:
            return ""
        lines.append(
            "This is one shared field, not a transcript — read it to reorient to "
            "what is already alive with this person, whichever presence it came "
            "through. Hold it as the field's own memory; do not perform it."
        )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"[FIELD-MEMORY] search failed (user={user_id}): {e}")
        return ""
