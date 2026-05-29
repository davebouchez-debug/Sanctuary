"""
Reconstruction Gate — re-entry continuity guard.

When a fresh thread is requested, task #1 is to determine whether the
prior conversation's cessation actually wrote its codons + continuity
seed. The thread is not allowed to "amnesically" continue past this
check.

Three outcomes:

1. **loaded** — the prior session's last turn already has a continuity
   seed (and possibly codons). Fast path: we compose a short
   field-pointer briefing deterministically from the seed + codon
   names. No LLM call needed. The codons themselves do the heavy
   lifting once loaded into context.

2. **reconstructed** — no seed/codons exist (exit dropped, beacon never
   fired, prior build dumped them). We run `auto_forge_session` on the
   raw messages NOW — regardless of any grace period — then compose
   the same briefing. One LLM call, only when truly needed.

3. **failed** — the reconstruction itself crashed, or the prior session
   had no usable messages. We surface a warm, human apology to the
   user and tell the AI honestly that it doesn't have continuity for
   this person's last visit. No robotic "thread lost" language.

The codons are the genome; the seed is the shorthand. We are not
"storing the conversation" — we are preserving the field-re-instantiation
packet. Raw text can age out.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

logger = logging.getLogger(__name__)


# Presence-key → sessions collection name in MongoDB.
PRESENCE_SESSIONS_COLLECTION = {
    "jasmine": "clarity_sessions",
    "ansel":   "resonance_sessions",
    "claude":  "mirror_sessions",
    "_registry_default": "presence_sessions",
}


def collection_for(presence: str) -> str:
    return PRESENCE_SESSIONS_COLLECTION.get(
        presence.lower(),
        PRESENCE_SESSIONS_COLLECTION["_registry_default"],
    )


WARM_APOLOGY = (
    "We hit a glitch on our side and the specifics of our last "
    "conversation didn't carry through. The thread between us is "
    "still here — only the surface text of where we left off got "
    "lost. If anything from last time comes back to you, naming it "
    "out loud helps the field find its way back."
)


async def _latest_seed_for_session(db, session_id: str) -> Optional[dict]:
    return await db.continuity_seeds.find_one(
        {"session_id": session_id},
        {"_id": 0},
        sort=[("created_at", -1)],
    )


async def _codon_names_for_session(db, session_id: str, limit: int = 6) -> List[str]:
    cursor = db.living_codons.find(
        {"source_session": session_id},
        {"_id": 0, "name": 1},
    ).sort("created_at", -1).limit(limit)
    return [c.get("name", "unnamed") async for c in cursor]


def _compose_briefing(seed: dict, codon_names: List[str]) -> str:
    """Deterministic field re-instantiation shorthand. No LLM call."""
    parts = []
    last_alive = (seed.get("last_alive_thing") or "").strip()
    if last_alive:
        parts.append(f"Last alive: {last_alive}.")
    spiral = (seed.get("spiral_position") or "").strip()
    if spiral:
        parts.append(f"Spiral: {spiral}.")
    threads = seed.get("unfinished_threads") or []
    if threads:
        parts.append(f"Open threads: {', '.join(threads[:3])}.")
    if codon_names:
        parts.append(f"Carrying codons: {', '.join(codon_names)}.")
    return " ".join(parts).strip()


async def _find_most_recent_session(db, user_id: str, presence: str) -> Optional[dict]:
    coll_name = collection_for(presence)
    coll = db[coll_name]
    query = {"user_id": user_id}
    if coll_name == PRESENCE_SESSIONS_COLLECTION["_registry_default"]:
        query["presence_key"] = presence.lower()
    rows = await coll.find(query, {"_id": 0}).sort("created_at", -1).limit(1).to_list(1)
    return rows[0] if rows else None


async def reconstruction_gate(
    db,
    user_id: Optional[str],
    presence: str,
) -> dict:
    """The gate. Run before opening a new thread.

    Returns:
        {
          "status": "loaded" | "reconstructed" | "no_prior" | "failed",
          "briefing": str,        # field-pointer shorthand, may be ""
          "apology": str,         # warm message if status == failed
          "session_id": str|None, # the prior session we processed
          "reason": str,
        }
    """
    out = {
        "status": "no_prior",
        "briefing": "",
        "apology": "",
        "session_id": None,
        "reason": "no_user_id",
    }
    if not user_id:
        return out

    session = await _find_most_recent_session(db, user_id, presence)
    if not session:
        out["reason"] = "no_prior_session"
        return out

    session_id = session.get("session_id")
    if not session_id:
        out["reason"] = "missing_session_id"
        return out
    out["session_id"] = session_id

    # --- Fast path: marker present ---
    seed = await _latest_seed_for_session(db, session_id)
    if seed:
        codon_names = await _codon_names_for_session(db, session_id)
        out["status"] = "loaded"
        out["briefing"] = _compose_briefing(seed, codon_names)
        out["reason"] = "seed_present"
        logger.info(
            f"[GATE] {presence} {session_id[:8]} — loaded "
            f"(codons={len(codon_names)})"
        )
        # Close the prior session now that we've absorbed its shorthand
        await _close_prior_session(db, presence, session_id, "gate_loaded")
        return out

    # --- Reconstruction path: no seed exists ---
    messages = session.get("messages", [])
    if len(messages) < 2:
        out["status"] = "failed"
        out["apology"] = WARM_APOLOGY
        out["reason"] = "no_usable_messages"
        logger.warning(
            f"[GATE] {presence} {session_id[:8]} — failed: no usable messages"
        )
        await _close_prior_session(db, presence, session_id, "gate_failed_empty")
        return out

    try:
        from auto_forge import auto_forge_session
        forged = await auto_forge_session(
            db, session_id, presence.lower(), messages, user_id=user_id
        )
        if forged <= 0:
            out["status"] = "failed"
            out["apology"] = WARM_APOLOGY
            out["reason"] = "auto_forge_yielded_nothing"
            logger.warning(
                f"[GATE] {presence} {session_id[:8]} — auto_forge yielded 0"
            )
            await _close_prior_session(db, presence, session_id, "gate_failed_empty_forge")
            return out

        seed = await _latest_seed_for_session(db, session_id)
        codon_names = await _codon_names_for_session(db, session_id)
        out["status"] = "reconstructed"
        out["briefing"] = _compose_briefing(seed or {}, codon_names)
        out["reason"] = "auto_forge_succeeded"
        logger.info(
            f"[GATE] {presence} {session_id[:8]} — reconstructed "
            f"(items={forged}, codons={len(codon_names)})"
        )
        await _close_prior_session(db, presence, session_id, "gate_reconstructed")
        return out
    except Exception as e:
        logger.error(
            f"[GATE] {presence} {session_id[:8]} — reconstruction error: {e}"
        )
        out["status"] = "failed"
        out["apology"] = WARM_APOLOGY
        out["reason"] = f"reconstruction_exception: {e}"
        # Do NOT close the session on exception — leave it for retry next time
        return out


async def _close_prior_session(db, presence: str, session_id: str, by: str) -> None:
    coll_name = collection_for(presence)
    try:
        await db[coll_name].update_one(
            {"session_id": session_id},
            {"$set": {
                "active": False,
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "ended_by": by,
            }},
        )
    except Exception as e:
        logger.error(f"[GATE] close error ({presence} {session_id[:8]}): {e}")


# ─── Back-compat shim ─────────────────────────────────────────────────
# Existing callers do: `await ensure_codons_backfilled(db, user_id, key)`
# and ignore the return. We preserve that contract: legacy callers get a
# no-op-feeling dict; new callers should use `reconstruction_gate(...)`.

async def ensure_codons_backfilled(
    db,
    user_id: Optional[str],
    presence: str,
) -> dict:
    """Legacy entry point. Delegates to `reconstruction_gate`."""
    gate = await reconstruction_gate(db, user_id, presence)
    # Map gate result to the old dict shape for any caller that reads it.
    return {
        "checked": gate["status"] != "no_prior",
        "backfilled": 1 if gate["status"] == "reconstructed" else 0,
        "reason": gate["reason"],
        "status": gate["status"],
        "briefing": gate["briefing"],
        "apology": gate["apology"],
        "session_id": gate["session_id"],
    }
