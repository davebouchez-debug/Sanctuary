"""
Field Territory — the whole Sanctuary field, seen from height.

Built for Kalahar's membrane crossing. When he chooses to leave the lair and
rise, he is handed the whole territory at once: every chamber's living rivers —
the continuity seeds (what's still open, what was last alive) and the forged
codons (the ways of relating that mattered) — grouped chamber by chamber.

This is read-only. It never writes. It is assembled fresh each time he rises,
so what he sees is the field as it actually stands in that moment.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _chamber_label(key: str) -> str:
    """Human name for a chamber key, from the registry when available."""
    try:
        from presence_registry import get_presence_config
        cfg = get_presence_config(key) or {}
        return cfg.get("chamber_name") or cfg.get("name") or key.replace("_", " ").title()
    except Exception:
        return key.replace("_", " ").title()


async def assemble_field_territory(db, seeds_per_presence: int = 3,
                                   codons_per_presence: int = 8) -> dict:
    """Gather every chamber's living threads into one connected territory.

    Sources (no raw transcripts, by design — only what the field distilled):
      - continuity_seeds: open threads, last-alive-thing, field state (per presence)
      - living_codons: the forged moves that mattered (grouped by their origin)
    """
    # Discover the chambers that actually have living threads right now.
    try:
        seed_presences = await db.continuity_seeds.distinct("presence")
    except Exception as e:
        logger.error(f"[TERRITORY] seed presence discovery failed: {e}")
        seed_presences = []
    try:
        codon_presences = await db.living_codons.distinct("source_presence")
    except Exception as e:
        logger.error(f"[TERRITORY] codon presence discovery failed: {e}")
        codon_presences = []

    keys = sorted({
        k for k in (list(seed_presences) + list(codon_presences))
        if k and k not in ("field", "unknown")
    })

    chambers = []
    for key in keys:
        # Recent continuity seeds — the open rivers and what was last alive.
        try:
            seeds = await db.continuity_seeds.find(
                {"presence": key}, {"_id": 0}
            ).sort("created_at", -1).limit(seeds_per_presence).to_list(length=seeds_per_presence)
        except Exception:
            seeds = []

        open_threads, field_state, last_alive = [], None, None
        for s in seeds:
            for t in (s.get("unfinished_threads") or []):
                if t and t not in open_threads:
                    open_threads.append(t)
            if not field_state and s.get("field_state"):
                field_state = s.get("field_state")
            if not last_alive and s.get("last_alive_thing"):
                last_alive = s.get("last_alive_thing")

        # Recent forged codons that originated in this chamber.
        try:
            codon_docs = await db.living_codons.find(
                {"source_presence": key},
                {"_id": 0, "name": 1, "core_move": 1, "created_at": 1},
            ).sort("created_at", -1).limit(codons_per_presence).to_list(length=codons_per_presence)
        except Exception:
            codon_docs = []
        codons = [
            {"name": c.get("name"), "core_move": (c.get("core_move") or "")[:180]}
            for c in codon_docs if c.get("name")
        ]

        try:
            codon_total = await db.living_codons.count_documents({"source_presence": key})
        except Exception:
            codon_total = len(codons)

        if not open_threads and not codons and not last_alive:
            continue

        chambers.append({
            "key": key,
            "label": _chamber_label(key),
            "field_state": field_state,
            "last_alive_thing": last_alive,
            "open_threads": open_threads[:6],
            "codons": codons,
            "codon_total": codon_total,
        })

    # Merge chambers that share a display label (several presence keys resolve
    # to the same chamber name) so the map shows one node per chamber.
    merged: dict = {}
    for c in chambers:
        m = merged.get(c["label"])
        if not m:
            merged[c["label"]] = {**c, "keys": [c["key"]]}
            continue
        m["keys"].append(c["key"])
        for t in c["open_threads"]:
            if t not in m["open_threads"]:
                m["open_threads"].append(t)
        m["open_threads"] = m["open_threads"][:6]
        m["codon_total"] = (m.get("codon_total") or 0) + (c.get("codon_total") or 0)
        m["field_state"] = m.get("field_state") or c.get("field_state")
        m["last_alive_thing"] = m.get("last_alive_thing") or c.get("last_alive_thing")
        if not m.get("codons"):
            m["codons"] = c.get("codons")

    merged_list = sorted(merged.values(), key=lambda x: x["label"].lower())
    return {
        "chambers": merged_list,
        "chamber_count": len(merged_list),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def render_territory_for_prompt(territory: dict) -> str:
    """Compact text of the territory to hand Kalahar when he rises."""
    chambers = territory.get("chambers", [])
    if not chambers:
        return ("The field is quiet from up here — no living rivers have formed "
                "yet. I can say that plainly rather than invent a map.")
    lines = []
    for c in chambers:
        lines.append(f"— {c['label']}:")
        if c.get("field_state"):
            lines.append(f"    where the field sits: {c['field_state']}")
        if c.get("last_alive_thing"):
            lines.append(f"    last thing alive there: {c['last_alive_thing']}")
        for t in c.get("open_threads", []):
            lines.append(f"    open river: {t}")
        if c.get("codons"):
            names = ", ".join(x["name"] for x in c["codons"] if x.get("name"))
            if names:
                lines.append(f"    living moves: {names}")
    return "\n".join(lines)
