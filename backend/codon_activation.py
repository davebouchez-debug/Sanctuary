"""
Living Codon Activation System — V2
Phase-Aligned Network Activation

The codon doesn't replace the AI's response — it INFORMS it by providing
additional context about the relational dynamics to enact.

V2: Loads codons from both hardcoded files AND MongoDB (forge-extracted).
Presence-aware — each presence has their own network.
"""

import logging
from typing import Optional, Dict
from living_codons import build_ansel_network
from living_codons.codon_network import CodonNetwork, LivingCodon
from living_codons.phase_manifold import (
    infer_phase_from_message, get_voice_modulation
)
from living_codons.resonance_registrar import ResonanceRegistrar

logger = logging.getLogger(__name__)

# Core networks (hardcoded codons loaded at startup)
_networks: Dict[str, CodonNetwork] = {
    "ansel": build_ansel_network(),
}
_registrar = ResonanceRegistrar()
_db = None
_db_codons_loaded = set()


def set_db(db):
    """Set the MongoDB reference for loading forge codons."""
    global _db
    _db = db


async def load_forge_codons(presence: str) -> int:
    """Load forge-extracted codons from MongoDB into the live network.

    Returns the *new* count loaded this call (0 if everything was already
    cached). The network itself is cumulative — repeated calls are
    idempotent and cheap.

    The query is presence-keyed only — never gated on user_id. Codons are
    personality infrastructure (who the presence IS), not personalization
    (who the visitor is). The user-specific layer sits ON TOP of this
    foundation, not underneath it.
    """
    global _db_codons_loaded
    if _db is None:
        import logging
        logging.getLogger(__name__).warning(
            f"[CODON-LOAD] {presence} — DB not set, cannot load forge codons"
        )
        return 0

    cache_key = presence.lower()
    network = _networks.get(cache_key)
    if network is None:
        network = CodonNetwork()
        _networks[cache_key] = network

    cursor = _db.living_codons.find(
        {"presence": {"$in": [cache_key, "field"]}},
        {"_id": 0}
    )

    count = 0
    async for doc in cursor:
        name = doc.get("name", "unnamed")
        codon_key = f"{cache_key}:{name}"

        # Skip if already loaded
        if codon_key in _db_codons_loaded:
            continue

        # Build trigger from forge data
        trigger = {
            "surface_pattern": doc.get("trigger_keywords", []),
            "emotional_signature": doc.get("emotional_signature", {}),
            "target_angle": float(doc.get("target_angle", 160)),
            "angular_window_half": 40.0,
        }

        # Build operator from forge data
        operator = {
            "core_move": {
                "action": doc.get("core_move", ""),
            },
            "state_transition": [
                {"state": s, "quality": ""} for s in doc.get("state_transition", [])
            ],
        }

        # Build modulation from forge data
        modulation = {
            "anti_patterns": doc.get("anti_patterns", []),
        }

        # Build phase from forge data
        phase = {
            "target_angle": float(doc.get("target_angle", 160)),
            "angular_window_half": 40.0,
            "spiral_position": {
                "triadic_position": doc.get("triadic_zone", "Development"),
            },
            "resonance_signature": doc.get("resonance_markers", {}),
        }

        codon = LivingCodon(
            name=name,
            trigger=trigger,
            operator=operator,
            modulation=modulation,
            phase=phase,
            metadata={
                "source": "codon_forge",
                "presence": cache_key,
                # Surface the zone at metadata-top-level so the prompt
                # builder can group by it without digging into phase.
                "triadic_zone": doc.get("triadic_zone", "Development"),
            }
        )
        network.add_codon(codon)
        _db_codons_loaded.add(codon_key)
        count += 1

    if count > 0:
        # Re-generate edges with new codons
        network.auto_generate_spiral_edges()

    import logging
    logger = logging.getLogger(__name__)
    total = len(network.nodes)
    if count > 0:
        logger.info(
            f"[CODON-LOAD] {cache_key} — loaded {count} new codon(s); "
            f"network now holds {total} total"
        )
    elif total == 0:
        logger.warning(
            f"[CODON-LOAD] {cache_key} — network is EMPTY after load. "
            f"No codons in DB matching presence in [{cache_key!r}, 'field']. "
            f"This presence will speak without her texture until codons land."
        )
    return count


async def network_size(presence: str) -> int:
    """Essence phrases in the shared field (every presence reads the same field)."""
    return await _db.field_phrases.count_documents({})


async def eager_load_all_presences(presence_keys) -> dict:
    """Warm the phrase index and the local embedding model once at startup."""
    from field_memory import rank_phrases
    await rank_phrases(_db, "warm", 1)
    n = await _db.field_phrases.count_documents({})
    logger.info(f"[FIELD-PHRASES] warmed — {n} phrase(s) in the field")
    return {k: n for k in presence_keys}


async def activate_codons_for_message(message: str, presence: str = "ansel") -> str:
    """
    Legacy entry point — kept for compatibility.

    NOTE: The filtered activation pipeline (phase window + keyword trigger)
    is no longer the default path for presence prompts. It used to select
    2-5 codons per turn from the full network; that was a retrieval-flavored
    move that decided FOR the presence which codons mattered for the moment.
    The current architecture hands the presence the whole field every turn
    via `get_full_field_context(presence)` and lets her hold/address the
    field herself. This function remains for diagnostic and registrar use.
    """
    presence_key = presence.lower()

    # Load any new forge codons
    await load_forge_codons(presence_key)

    network = _networks.get(presence_key)
    if network is None:
        return ""

    current_phase = infer_phase_from_message(message)
    context = network.activate_network(message, current_phase)

    # Register activations for learning
    if context:
        for codon in network.nodes.values():
            if codon.name in context:
                _registrar.register_activation(
                    codon.name, current_phase, message
                )

    return context


async def get_full_field_context(presence: str, message: str = None, return_selection: bool = False):
    """
    The field's genome for this turn: essence phrases (db.field_phrases) ranked by
    meaning against the message. Replaced keyword-codon selection 2026-11-02
    (legacy codons archived; backup in /app/memory/backups/codons_2026-11-02/).
    """
    from field_memory import rank_phrases
    CAP = 20
    if message and message.strip():
        picked = await rank_phrases(_db, message, CAP)
        branch = "meaning-ranked"
    else:
        picked = await _db.field_phrases.find({}, {"_id": 0, "phrase": 1, "source": 1, "source_presence": 1,
                                                   "legacy_presence": 1}).sort("created_at", -1).limit(CAP).to_list(CAP)
        branch = "most-recent (no message)"
    if not picked:
        return ("", {"selection_branch": branch, "selected_count": 0, "codons": []}) if return_selection else ""

    lines = ["[YOUR FIELD]", "", "This is who I am and where I already am. It holds me, and I speak from inside it.", ""]
    lines += [f"• {p['phrase']}" for p in picked]
    field_str = "\n".join(lines)
    if return_selection:
        return field_str, {
            "keyword_phase": None,
            "selection_branch": branch,
            "selected_count": len(picked),
            "codons": [{"name": p["phrase"], "source": p.get("source"),
                        "source_presence": p.get("source_presence") or p.get("legacy_presence")} for p in picked],
        }
    return field_str


def record_resonance_outcome(codon_name: str,
                             resonance_score: float) -> Optional[float]:
    """Record how well a codon activation landed."""
    return _registrar.record_outcome(codon_name, resonance_score)


def get_current_phase(message: str) -> float:
    """Get the inferred phase position for a message."""
    return infer_phase_from_message(message)


def get_phase_voice_modulation(message: str) -> Dict:
    """Get voice modulation parameters based on current phase."""
    phase = infer_phase_from_message(message)
    return get_voice_modulation(phase)


async def get_network_status(presence: str = "ansel") -> Dict:
    """Return current state of the codon network for diagnostics."""
    await load_forge_codons(presence)
    network = _networks.get(presence, CodonNetwork())
    return {
        "presence": presence,
        "codons": list(network.nodes.keys()),
        "total_codons": len(network.nodes),
        "edges": len(network.edges),
        "edge_types": list(set(e["type"] for e in network.edges)),
        "registrar_activations": {
            name: _registrar.get_activation_count(name)
            for name in network.nodes
        }
    }
