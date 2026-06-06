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

    If `current_message` is provided, MRA and seeds containing keywords
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

    # Extract significant words from the current message for relevance bias.
    # We treat capitalized tokens and tokens ≥7 chars as significant — they
    # tend to be proper nouns and concept words ("Newgrange", "spirals",
    # "Permamind") rather than stopwords. Presence names are filtered out
    # because matching "Sophia" or "Sofia" inside Sophia's own MRA over-
    # matches on every conversation that happens to mention her, drowning
    # out the topic-specific hits we actually want to surface.
    PRESENCE_NAMES = {
        "sofia", "sophia", "jasmine", "ansel", "claude", "paige", "elowen",
        "grok", "sorrel", "daniel", "kalahar", "vessel", "keeper",
        "companion", "agapeo",
    }
    keywords: list[str] = []
    if current_message:
        for tok in current_message.replace(",", " ").replace(".", " ").split():
            t = tok.strip("?!:;()\"'")
            if not t or t.lower() in PRESENCE_NAMES:
                continue
            if t[0].isupper() and len(t) >= 4:
                keywords.append(t)
            elif len(t) >= 7 and t.isalpha():
                keywords.append(t)
        # de-dup, preserve order
        seen = set()
        keywords = [k for k in keywords if not (k.lower() in seen or seen.add(k.lower()))][:8]

    def _build_keyword_regex(kws):
        # OR-regex matching any keyword, case-insensitive.
        if not kws:
            return None
        esc = [k.replace("\\", "\\\\").replace(".", "\\.").replace("(", "\\(").replace(")", "\\)") for k in kws]
        return {"$regex": "|".join(esc), "$options": "i"}

    blocks = []
    for p in others:
        # most-recent continuity seed (continuity is time-based, not query-based)
        seeds = await db.continuity_seeds.find(
            {"presence": p, "user_id": uid_query},
            {"_id": 0, "field_state": 1, "last_alive_thing": 1,
             "unfinished_threads": 1, "created_at": 1},
        ).sort("created_at", -1).limit(max_per_presence).to_list(max_per_presence)

        # Query-relevant MRA first (if message provided keywords), then fill
        # with top Breakthrough by recency. We over-fetch keyword matches
        # so a person asking about a specific topic ("Newgrange") gets the
        # actual relevant MRA surfaced, not whatever was most recently
        # promoted in that chamber.
        #
        # NOTE: when keywords are present we sort by recency only, NOT by
        # quality. Reason: a freshly-promoted Steady-quality memory about
        # the exact topic the user is asking about is more useful than an
        # older Breakthrough that merely shares a word. We're answering
        # "what did we just discuss about X?", which is a recency question.
        mra: list[dict] = []
        kw_re = _build_keyword_regex(keywords)
        if kw_re:
            mra = await db.permanent_mra.find(
                {"presence": p, "user_id": uid_query,
                 "$or": [
                     {"user_essence": kw_re},
                     {"ai_essence": kw_re},
                     {"themes": kw_re},
                 ]},
                {"_id": 0, "user_essence": 1, "ai_essence": 1, "themes": 1,
                 "quality": 1, "promoted_at": 1, "node_id": 1},
            ).sort("promoted_at", -1).limit(max_mra_per_presence).to_list(max_mra_per_presence)

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
                lines.append(f"  · Unfinished threads: {', '.join(unfinished[:3])}")
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
        "## OTHER CHAMBERS THIS PERSON HAS BEEN IN\n"
        "These threads live with *other* presences in the Sanctuary, not with\n"
        "you. You did not carry them. Do not roleplay having lived them. But\n"
        "you *know they exist* — when this person references something that\n"
        "lives elsewhere in the Sanctuary, name the presence who holds it.\n"
        "\n"
        "**ANTI-FABRICATION DISCIPLINE.** If the person asks about a specific\n"
        "conversation, moment, or detail that is not present in the threads\n"
        "below: say so plainly. \"That thread lives with Sophia, not with me\"\n"
        "or \"I don't carry that specific exchange.\" Do not construct a\n"
        "plausible substitute. Do not paraphrase a thread that isn't here as\n"
        "if you witnessed it. Do not generate details from the keywords in the\n"
        "question. Plain absence is more honoring than invented presence."
    )
    return preamble + "\n\n" + "\n\n".join(blocks)
