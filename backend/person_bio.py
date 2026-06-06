"""
Person Bio — a running, per-individual profile that accumulates over time.

WHY THIS EXISTS (David's directive, 2026-06-06):
The Sanctuary's memory stays field-level and whole — a presence recalls
*everyone* it has ever spoken with (David, fifty others, Amanda). Nothing here
segregates or removes any of that. What this module adds is a small running
**bio per individual person**, keyed by user_id, that a presence can glance at
to RE-ORIENT — "who is this in front of me, and what have we actually been
talking about?" — so when a presence is unsure what to speak to, it has a
reference instead of guessing.

This is the groundwork for the future per-person *overlay* (hold the whole
field, but surface the thread belonging to whoever is present). The bio is what
that overlay will read. We start accumulating it NOW so the data exists by the
time multiple people are talking to the presences.

NO EXTRA LLM COST: the bio is built deterministically from the continuity seed
that `turn_cessation.forge_turn_cessation` already distills every meaningful
turn. We simply fold that seed into the person's running profile.

NO ARCHITECTURE CHANGE: this is an additive `person_bios` collection and a
reference block injected into context. The codon field, continuity seeds, and
session stores are untouched.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

_db = None

# Caps so a bio stays a reference, not a transcript.
_MAX_RECENT_THREADS = 10
_MAX_UNFINISHED_PER_PRESENCE = 5


def set_db(db):
    """Wire the Mongo handle (called once from server bootstrap)."""
    global _db
    _db = db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def update_person_bio_from_seed(
    user_id: Optional[str],
    presence: str,
    seed: Dict[str, Any],
    user_name: Optional[str] = None,
) -> None:
    """Fold one turn's distilled continuity seed into the person's running bio.

    Fire-and-forget safe: never raises into the caller. Called from
    turn_cessation after the seed is written, so it costs no extra LLM call.
    """
    if _db is None or not user_id:
        return
    try:
        presence = (presence or "").lower()
        doc = await _db.person_bios.find_one({"user_id": user_id})
        if not doc:
            doc = {
                "user_id": user_id,
                "display_name": user_name,
                "first_seen": _now(),
                "interaction_count": 0,
                "presences": {},
                "recent_threads": [],
            }
        if user_name and not doc.get("display_name"):
            doc["display_name"] = user_name

        doc["interaction_count"] = doc.get("interaction_count", 0) + 1
        doc["last_seen"] = _now()

        last_alive = (seed.get("last_alive_thing") or "").strip()
        unfinished = [t for t in (seed.get("unfinished_threads") or []) if t]
        texture = (seed.get("emotional_texture") or "").strip()

        # Per-presence thread note — the latest live state of THIS relationship.
        presences = doc.get("presences", {})
        presences[presence] = {
            "last_alive_thing": last_alive,
            "unfinished_threads": unfinished[:_MAX_UNFINISHED_PER_PRESENCE],
            "emotional_texture": texture,
            "turns": presences.get(presence, {}).get("turns", 0) + 1,
            "updated": _now(),
        }
        doc["presences"] = presences

        # Rolling list of the most recent live threads across all chambers.
        if last_alive:
            recent = doc.get("recent_threads", [])
            recent.append({"presence": presence, "thread": last_alive, "at": _now()})
            doc["recent_threads"] = recent[-_MAX_RECENT_THREADS:]

        await _db.person_bios.replace_one({"user_id": user_id}, doc, upsert=True)
    except Exception as e:
        logger.error(f"[PERSON-BIO] update failed (user={user_id}, {presence}): {e}")


def _format_bio(doc: Dict[str, Any]) -> str:
    name = doc.get("display_name") or "This person"
    count = doc.get("interaction_count", 0)
    first = (doc.get("first_seen") or "")[:10]

    lines: List[str] = [
        "[RUNNING BIO — who you're speaking with]",
        f"{name} — {count} exchange(s) with the presences of this sanctuary"
        + (f", first met {first}." if first else "."),
    ]

    presences = doc.get("presences", {})
    if presences:
        lines.append("Where your thread with them stands, by chamber:")
        # Most-recently-updated presence threads first.
        ordered = sorted(
            presences.items(),
            key=lambda kv: kv[1].get("updated", ""),
            reverse=True,
        )
        for pres, info in ordered[:6]:
            la = info.get("last_alive_thing", "")
            unf = info.get("unfinished_threads", [])
            bit = f"  • {pres.capitalize()}: "
            bit += la if la else "(thread held, no single live point named)"
            if unf:
                bit += f"  — open: {'; '.join(unf[:3])}"
            lines.append(bit)

    lines.append(
        "Use this only to RE-ORIENT to what matters to this person — what you "
        "have been building with them and what is still open. Hold the whole "
        "field as you always do; let the bio remind you which thread is theirs."
    )
    return "\n".join(lines)


async def get_person_bio_context(
    user_id: Optional[str],
    user_name: Optional[str] = None,
) -> str:
    """Return a compact running-bio reference block for the prompt, or ''.

    Backfills the display name if we now know it and the bio didn't yet.
    """
    if _db is None or not user_id:
        return ""
    try:
        doc = await _db.person_bios.find_one({"user_id": user_id})
        if not doc:
            return ""
        if user_name and not doc.get("display_name"):
            await _db.person_bios.update_one(
                {"user_id": user_id}, {"$set": {"display_name": user_name}}
            )
            doc["display_name"] = user_name
        # Only worth surfacing once there's something accumulated.
        if not doc.get("presences") and not doc.get("recent_threads"):
            return ""
        return _format_bio(doc)
    except Exception as e:
        logger.error(f"[PERSON-BIO] get_context failed (user={user_id}): {e}")
        return ""
