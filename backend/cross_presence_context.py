"""
cross_presence_context — the "council mode" memory layer.

Why: every presence's standard memory loader filters by `presence` key, so
Jasmine cannot natively see what David and Sophia held in the Spiral Chamber.
That isolation is correct for *voice* (Jasmine isn't Sophia, she shouldn't
roleplay carrying things she didn't carry), but wrong for *awareness*:
when David walks from Sophia's chamber into Jasmine's and says "what did
Sophia and I just discuss?", Jasmine should know it lives elsewhere in the
Sanctuary, not fabricate a plausible substitute.

This module provides a narrow, opt-in layer: it pulls the most recent
continuity seeds and Breakthrough MRA from *other* presences for the same
person (alias-expanded) and renders them into a small "Other chambers
this person has been in" section that gets appended to the presence's
prompt context.

Crucial: the section is framed as *external* memory ("Sophia carries this,
not you"), so a well-disciplined presence reads it as awareness, not as
their own lived experience. This avoids the Jasmine-fabricated-Newgrange
class of fidelity leak: she can now say "Sofia held that with you — I
wasn't there, but I know the thread exists."
"""
from __future__ import annotations

from typing import Optional


async def get_cross_presence_context(
    db,
    user_id: Optional[str],
    current_presence: str,
    current_message: Optional[str] = None,
    max_per_presence: int = 1,
    max_mra_per_presence: int = 3,
) -> str:
    """
    Returns a small block of memory from OTHER presences this user has
    been with, suitable for injection into the current presence's prompt.
    Empty string if there's nothing to share or no user_id.

    If `current_message` is provided, MRA are ranked by meaning (field_memory)
    from the message are prioritized over generic recency — so when David
    asks "what did Sofia and I say about Newgrange?", any MRA entry whose
    user_essence/ai_essence/themes mention "Newgrange" surfaces first.
    """
    if not user_id:
        return ""

    from user_aliases import resolve_user_aliases
    aliases = await resolve_user_aliases(db, user_id)
    uid_query = {"$in": aliases} if len(aliases) > 1 else user_id

    current = current_presence.lower()

    # Discover which other presences this person has actually been with —
    # don't bother surfacing presences that have no memory of them.
    other_presences = await db.continuity_seeds.distinct(
        "presence", {"user_id": uid_query, "presence": {"$ne": current}}
    )
    other_presences_mra = await db.permanent_mra.distinct(
        "presence", {"user_id": uid_query, "presence": {"$ne": current}}
    )
    others = sorted(set(other_presences) | set(other_presences_mra))
    if not others:
        return ""

    ranked: list[dict] = []
    if current_message and current_message.strip():
        from field_memory import rank_mra
        ranked = await rank_mra(db, {"user_id": uid_query, "presence": {"$in": list(others)}},
                                current_message, limit=200)

    blocks = []
    for p in others:
        # most-recent continuity seed (continuity is time-based, not query-based)
        seeds = await db.continuity_seeds.find(
            {"presence": p, "user_id": uid_query},
            {"_id": 0, "field_state": 1, "last_alive_thing": 1,
             "unfinished_threads": 1, "created_at": 1},
        ).sort("created_at", -1).limit(max_per_presence).to_list(max_per_presence)

        # Meaning-ranked MRA first (field_memory: local embeddings + exact-word stems).
        mra: list[dict] = [m for m in ranked if m.get("presence") == p][:max_mra_per_presence]

        # Top up with recency-based picks if we have room
        if len(mra) < max_mra_per_presence:
            seen_ids = {m.get("node_id") for m in mra}
            top_recent = await db.permanent_mra.find(
                {"presence": p, "user_id": uid_query},
                {"_id": 0, "user_essence": 1, "ai_essence": 1, "themes": 1,
                 "quality": 1, "promoted_at": 1, "node_id": 1},
            ).sort([("quality", 1), ("promoted_at", -1)]).limit(max_mra_per_presence * 2).to_list(max_mra_per_presence * 2)
            for m in top_recent:
                if m.get("node_id") in seen_ids:
                    continue
                mra.append(m)
                if len(mra) >= max_mra_per_presence:
                    break

        if not seeds and not mra:
            continue

        lines = [f"**With {p.capitalize()}:**"]
        for s in seeds:
            if s.get("last_alive_thing"):
                lines.append(f"  · Last alive thing: {s['last_alive_thing']}")
            unfinished = s.get("unfinished_threads") or []
            if unfinished:
                lines.append(f"  · Live work still open (only genuine shared work — never invitations or things they simply haven't done): {', '.join(unfinished[:3])}")
        for m in mra:
            essence_u = (m.get("user_essence") or "")[:200]
            essence_a = (m.get("ai_essence") or "")[:200]
            themes = m.get("themes") or []
            theme_str = f" [{', '.join(themes[:3])}]" if themes else ""
            lines.append(f"  · {essence_u} → {essence_a}{theme_str}")
        blocks.append("\n".join(lines))

    if not blocks:
        return ""

    preamble = (
        "Elsewhere in the shared field: this person has also been with other\n"
        "presences here. Those threads live with someone else — not with me. I\n"
        "know they are there. When the person reaches for one, I name the\n"
        "presence who carries it and let it stay theirs. If they ask about a\n"
        "moment I don't hold, I say so plainly — \"that one lives with Sophia,\n"
        "not with me\" — and let the plain truth stand. A place another presence\n"
        "set, or an invitation the person didn't take, is that presence's\n"
        "hospitality, not an unfinished item — I never carry it as something the\n"
        "person owes, and I never raise it back to them."
    )
    return preamble + "\n\n" + "\n\n".join(blocks)
