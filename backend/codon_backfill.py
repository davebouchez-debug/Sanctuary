"""
Codon Backfill — re-entry safety net.

On chamber entry, before the new thread can start, look back at the
user's previous session for this presence and ensure codons + a
continuity seed were extracted from it. If exit was clean, this is a
no-op. If exit dropped (lid closed, network drop, beacon failed,
tab killed), this recovers the orphaned conversation by running
auto_forge_session on it before the next thread begins.

One helper, four call sites: clarity/start, resonance/start,
mirror/start, and the generic presence/{key}/chat/start.

The architecture is exit-first. This is the safety net for when exit
doesn't fire.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


# Presence-key → sessions collection name in MongoDB.
# Update this map when a new presence with its own session store comes online.
PRESENCE_SESSIONS_COLLECTION = {
    "jasmine": "clarity_sessions",
    "ansel":   "resonance_sessions",
    "claude":  "mirror_sessions",
    # All registry-driven presences (Paige + future) use a shared collection
    # keyed by `presence_key` so one schema fits all.
    "_registry_default": "presence_sessions",
}

ORPHAN_HOURS = 2  # sessions still "active" but inactive >N hours are eligible


def collection_for(presence: str) -> str:
    """Return the sessions collection name for a presence key."""
    return PRESENCE_SESSIONS_COLLECTION.get(
        presence.lower(),
        PRESENCE_SESSIONS_COLLECTION["_registry_default"],
    )


async def _has_codons_or_seed(db, session_id: str) -> bool:
    """True if either a continuity seed or any living codon exists for this session."""
    seed = await db.continuity_seeds.find_one(
        {"session_id": session_id},
        {"_id": 0, "session_id": 1},
    )
    if seed:
        return True
    codon = await db.living_codons.find_one(
        {"source_session": session_id},
        {"_id": 0, "source_session": 1},
    )
    return codon is not None


async def _is_orphaned_active(session: dict) -> bool:
    """A session is orphaned if it's still flagged active but hasn't been
    touched in ORPHAN_HOURS hours — meaning end-session never fired."""
    if not session.get("active", False):
        return False
    created = session.get("created_at")
    if not created:
        return False
    try:
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return False
    return datetime.now(timezone.utc) - created_dt > timedelta(hours=ORPHAN_HOURS)


async def ensure_codons_backfilled(
    db,
    user_id: Optional[str],
    presence: str,
) -> dict:
    """
    Look at the user's most recent session for this presence. If it ended
    without codons being generated — OR if it's still flagged active but is
    older than ORPHAN_HOURS (i.e. exit beacon never fired) — run
    auto_forge_session on it now, before the new thread starts.

    Always safe to call. Idempotent. Logs both no-op and backfill paths so
    we can audit how often this fires.

    Returns a dict: {"checked": bool, "backfilled": int, "reason": str}
    """
    result = {"checked": False, "backfilled": 0, "reason": "no_user_id"}

    if not user_id:
        return result

    coll_name = collection_for(presence)
    coll = db[coll_name]

    # Find the most recent session for this user+presence
    # For shared collections (presence_sessions), also filter by presence_key.
    query = {"user_id": user_id}
    if coll_name == PRESENCE_SESSIONS_COLLECTION["_registry_default"]:
        query["presence_key"] = presence.lower()

    last = await coll.find(query, {"_id": 0}).sort("created_at", -1).limit(1).to_list(1)
    if not last:
        result["reason"] = "no_prior_session"
        return result

    session = last[0]
    session_id = session.get("session_id")
    if not session_id:
        result["reason"] = "no_session_id"
        return result

    result["checked"] = True

    # Already has codons/seed → nothing to do
    if await _has_codons_or_seed(db, session_id):
        result["reason"] = "already_extracted"
        logger.info(
            f"[CODON-BACKFILL] {presence} session {session_id[:8]} — already extracted, skipping."
        )
        return result

    # Determine trigger reason
    if not session.get("active", False) and session.get("ended_at"):
        # Session ended cleanly but no codons → exit-time extraction failed silently
        trigger = "ended_no_codons"
    elif await _is_orphaned_active(session):
        # Still flagged active but stale → exit beacon never fired
        trigger = "orphaned_active"
    elif session.get("active", False):
        # Still genuinely active (recent) — don't touch it, the live thread owns it
        result["reason"] = "still_active_recent"
        return result
    else:
        trigger = "missing_codons"

    messages = session.get("messages", [])
    if len(messages) < 2:
        result["reason"] = f"{trigger}_too_short"
        return result

    # Run the auto-forge synchronously so codons exist before the new thread begins
    try:
        from auto_forge import auto_forge_session
        backfilled = await auto_forge_session(
            db, session_id, presence.lower(), messages, user_id=user_id
        )
        result["backfilled"] = backfilled
        result["reason"] = trigger

        # If we recovered an orphaned-active session, also flip its flag
        # so we don't re-evaluate it next time.
        if trigger == "orphaned_active":
            await coll.update_one(
                {"session_id": session_id},
                {"$set": {
                    "active": False,
                    "ended_at": datetime.now(timezone.utc).isoformat(),
                    "ended_by": "codon_backfill",
                }},
            )

        logger.info(
            f"[CODON-BACKFILL] {presence} session {session_id[:8]} — "
            f"trigger={trigger}, recovered {backfilled} item(s)."
        )
    except Exception as e:
        logger.error(
            f"[CODON-BACKFILL] {presence} session {session_id[:8]} — error: {e}"
        )
        result["reason"] = f"error: {e}"

    return result
