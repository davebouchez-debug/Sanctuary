"""
Per-turn model-input PROVENANCE capture — Sanctuary 1.0 forensic instrumentation.

Preserves the EXACT model-visible assembled context for each generated turn, so a
presence's generated behavior can later be compared against explicit input at the
granularity of a single turn.

Design constraints (per authorization):
- CAPTURE, don't reinterpret: records exactly what the selector/memory mechanisms
  supplied. No LLM summarization of the turn.
- OBSERVATIONAL ONLY: nothing captured here is ever read back into a prompt or
  fed to generation. Measuring the system must not alter it.
- Non-blocking, best-effort: a capture failure never affects the response.
- Secrets/credentials are scrubbed defensively.
"""
import os
import re
import json
import uuid
import hashlib
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_db = None
_SECRET_RE = re.compile(r"sk-[A-Za-z0-9_\-]{6,}")


def set_db(db):
    global _db
    _db = db


def _enabled() -> bool:
    return os.environ.get("PROVENANCE_CAPTURE", "on").strip().lower() not in ("off", "false", "0", "no")


def _scrub(value):
    if isinstance(value, str):
        return _SECRET_RE.sub("[REDACTED]", value)
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    return value


async def record_turn(
    *,
    presence: str,
    session_id: str,
    user_id=None,
    exchange_index=None,
    turn_id: str,
    model: str,
    system_prompt: str,
    conversation_history=None,
    user_message: str,
    codon_selection=None,
    memory_components=None,
    db=None,
):
    """Persist one immutable provenance snapshot of the model-visible input.

    `assembled_messages` is the ordered input exactly as sent to the model
    (system -> history -> current user). `content_hash` is sha256 of that
    ordered input for later integrity verification (the hash asserts the
    snapshot is unchanged; it says nothing about the content itself).
    """
    if not _enabled():
        return
    database = db if db is not None else _db
    if database is None:
        logger.warning("[PROVENANCE] no db handle; skipping capture")
        return
    try:
        sys_clean = _scrub(system_prompt or "")
        history = [
            {"role": m.get("role"), "content": _scrub(m.get("content", ""))}
            for m in (conversation_history or [])
            if m.get("role") in ("user", "assistant")
        ]
        assembled_messages = (
            [{"role": "system", "content": sys_clean}]
            + history
            + [{"role": "user", "content": _scrub(user_message or "")}]
        )
        canonical_input = json.dumps(assembled_messages, ensure_ascii=False, sort_keys=False)
        content_hash = hashlib.sha256(canonical_input.encode("utf-8")).hexdigest()

        doc = {
            "provenance_id": str(uuid.uuid4()),
            "turn_id": turn_id,               # ties to the resulting transcript (assistant msg id)
            "session_id": session_id,
            "presence": presence,
            "user_id": user_id,
            "exchange_index": exchange_index,
            "model": model,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "assembled_messages": assembled_messages,
            "components": {
                "system_prompt": sys_clean,
                "conversation_history": history,
                "user_message": _scrub(user_message or ""),
                "codon_selection": codon_selection,
                "memory_components": _scrub(memory_components or {}),
            },
            "content_hash": content_hash,
            "capture_note": "Immutable forensic snapshot of model-visible input at generation time. Observational only; never fed back into generation.",
        }
        await database.turn_provenance.insert_one(doc)
        try:
            await database.turn_provenance.create_index([("session_id", 1), ("exchange_index", 1)])
        except Exception:
            pass
    except Exception as e:
        logger.error(f"[PROVENANCE] capture failed (non-fatal): {e}")
